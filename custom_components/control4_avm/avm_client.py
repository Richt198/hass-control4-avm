"""Async UDP client for the Control4 AVM-16S1-B audio matrix.

Wire protocol (verified by packet capture and probing on a real device):

    Transport : UDP, default destination port 8750
    Encoding  : ASCII, CRLF-terminated
    Frame     : 0<verb><seq:4hex> <command> [<args>]\r\n
    Verbs     : s = SET, g = GET (client -> AVM)
                r = REPLY, t = NOTIFY (AVM -> client)
    Reply     : 0r<seq> <code> [<echo>]
                code "000" = OK, "v01" = value out of range, "n01" = unknown command
    Numbers   : 2-digit lowercase hex
                outputs/inputs 1..16 = 01..10; input 00 means "disconnected"
                volume  0..25  (0x00..0x19)  - default for unused outputs is 21
                bass    0..12  (0x00..0x0c)  - center 6
                treble  0..12  (0x00..0x0c)  - center 6
                balance 0..50  (0x00..0x32)  - center 25 (0=left, 50=right)
"""
from __future__ import annotations

import asyncio
import logging
from itertools import count

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 1.5
MAX_RETRIES = 1
INTER_COMMAND_DELAY = 0.0  # the Triad code used 25ms; AVM seems happy at 0


class AvmError(Exception):
    """Base error for AVM protocol failures."""


class AvmTimeout(AvmError):
    """Raised when the AVM doesn't reply within the timeout."""


class AvmReplyError(AvmError):
    """Raised when the AVM returns a non-zero reply code."""

    def __init__(self, code: str, request: str) -> None:
        super().__init__(f"AVM rejected {request!r}: code={code}")
        self.code = code
        self.request = request


class _AvmProtocol(asyncio.DatagramProtocol):
    """Routes incoming datagrams to per-seq Future objects."""

    def __init__(self) -> None:
        self.pending: dict[int, asyncio.Future[str]] = {}
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport):  # type: ignore[override]
        self.transport = transport

    def datagram_received(self, data, addr):  # type: ignore[override]
        try:
            text = data.decode("ascii", errors="replace").rstrip("\r\n")
        except Exception:
            return
        if len(text) < 6 or text[0] != "0" or text[1] != "r":
            return
        try:
            seq = int(text[2:6], 16)
        except ValueError:
            return
        fut = self.pending.pop(seq, None)
        if fut and not fut.done():
            fut.set_result(text)


class Avm16Client:
    """Talks to one AVM-16S1-B over UDP. Safe for concurrent use."""

    def __init__(self, host: str, port: int = 8750) -> None:
        self.host = host
        self.port = port
        self._protocol: _AvmProtocol | None = None
        self._transport: asyncio.DatagramTransport | None = None
        self._seq_iter = count(0x1000)
        self._connect_lock = asyncio.Lock()

    async def async_connect(self) -> None:
        async with self._connect_lock:
            if self._transport is not None:
                return
            loop = asyncio.get_running_loop()
            transport, protocol = await loop.create_datagram_endpoint(
                _AvmProtocol, remote_addr=(self.host, self.port)
            )
            self._transport = transport
            self._protocol = protocol  # type: ignore[assignment]

    async def async_close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._protocol = None

    def _next_seq(self) -> int:
        return next(self._seq_iter) & 0xFFFF

    async def _request(self, verb: str, command: str, *args: str) -> str:
        if self._protocol is None or self._transport is None:
            await self.async_connect()
        assert self._protocol is not None
        assert self._transport is not None

        last_err: Exception | None = None
        for _attempt in range(MAX_RETRIES + 1):
            seq = self._next_seq()
            payload_args = (" " + " ".join(args)) if args else ""
            packet = f"0{verb}{seq:04x} {command}{payload_args}\r\n".encode("ascii")
            fut: asyncio.Future[str] = asyncio.get_running_loop().create_future()
            self._protocol.pending[seq] = fut

            self._transport.sendto(packet)
            if INTER_COMMAND_DELAY:
                await asyncio.sleep(INTER_COMMAND_DELAY)

            try:
                reply = await asyncio.wait_for(fut, timeout=DEFAULT_TIMEOUT)
            except asyncio.TimeoutError:
                self._protocol.pending.pop(seq, None)
                last_err = AvmTimeout(f"No reply for {command}{payload_args}")
                continue

            tokens = reply.split(" ", 2)
            code = tokens[1] if len(tokens) >= 2 else "???"
            if code != "000":
                raise AvmReplyError(code, f"{command}{payload_args}")
            return tokens[2] if len(tokens) >= 3 else ""

        assert last_err is not None
        raise last_err

    @staticmethod
    def _hex(value: int) -> str:
        return f"{value:02x}"

    @staticmethod
    def _validate_output(output: int, max_outputs: int = 16) -> None:
        if not 1 <= output <= max_outputs:
            raise ValueError(f"output must be 1..{max_outputs}, got {output}")

    @staticmethod
    def _validate_range(value: int, low: int, high: int, name: str) -> None:
        if not low <= value <= high:
            raise ValueError(f"{name} must be {low}..{high}, got {value}")

    @staticmethod
    def _parse_value(echo: str) -> int:
        # echo: "c4.asw.<cmd> <out> <value>"
        return int(echo.rsplit(" ", 1)[-1], 16)

    # ---------------- Routing ----------------

    async def get_route(self, output: int) -> int:
        """Return the input number routed to ``output`` (0 = disconnected)."""
        self._validate_output(output)
        return self._parse_value(await self._request("g", "c4.asw.in", self._hex(output)))

    async def set_route(self, output: int, input_: int) -> None:
        self._validate_output(output)
        self._validate_range(input_, 0, 16, "input")
        await self._request("s", "c4.asw.out", self._hex(output), self._hex(input_))

    # ---------------- Volume / mute ----------------

    async def get_volume(self, output: int) -> int:
        self._validate_output(output)
        return self._parse_value(await self._request("g", "c4.asw.vol", self._hex(output)))

    async def set_volume(self, output: int, level: int) -> None:
        self._validate_output(output)
        self._validate_range(level, 0, 25, "volume")
        await self._request("s", "c4.asw.vol", self._hex(output), self._hex(level))

    async def get_mute(self, output: int) -> bool:
        self._validate_output(output)
        return self._parse_value(await self._request("g", "c4.asw.mute", self._hex(output))) == 1

    async def set_mute(self, output: int, mute: bool) -> None:
        self._validate_output(output)
        await self._request("s", "c4.asw.mute", self._hex(output), "01" if mute else "00")

    # ---------------- Tone ----------------

    async def get_bass(self, output: int) -> int:
        self._validate_output(output)
        return self._parse_value(await self._request("g", "c4.asw.bass", self._hex(output)))

    async def set_bass(self, output: int, value: int) -> None:
        self._validate_output(output)
        self._validate_range(value, 0, 12, "bass")
        await self._request("s", "c4.asw.bass", self._hex(output), self._hex(value))

    async def get_treble(self, output: int) -> int:
        self._validate_output(output)
        return self._parse_value(await self._request("g", "c4.asw.treble", self._hex(output)))

    async def set_treble(self, output: int, value: int) -> None:
        self._validate_output(output)
        self._validate_range(value, 0, 12, "treble")
        await self._request("s", "c4.asw.treble", self._hex(output), self._hex(value))

    async def get_balance(self, output: int) -> int:
        self._validate_output(output)
        return self._parse_value(await self._request("g", "c4.asw.bal", self._hex(output)))

    async def set_balance(self, output: int, value: int) -> None:
        self._validate_output(output)
        self._validate_range(value, 0, 50, "balance")
        await self._request("s", "c4.asw.bal", self._hex(output), self._hex(value))

    # ---------------- Bulk poll ----------------

    async def get_all_outputs(self, output_count: int = 16) -> dict[int, dict]:
        """Snapshot every output's full state. Used by the coordinator.

        Limits concurrent in-flight UDP requests — fully concurrent (96 at once)
        overwhelms the AVM and it drops packets. ~4 in-flight stays safely
        within its budget while still finishing in well under a second.
        """
        sem = asyncio.Semaphore(4)

        async def _one(out: int, getter) -> tuple[int, int | bool | None]:
            async with sem:
                try:
                    return out, await getter(out)
                except AvmError as err:
                    _LOGGER.debug("get failed for output %d: %s", out, err)
                    return out, None

        getters = [
            ("route", self.get_route),
            ("volume", self.get_volume),
            ("mute", self.get_mute),
            ("bass", self.get_bass),
            ("treble", self.get_treble),
            ("balance", self.get_balance),
        ]

        result: dict[int, dict] = {
            out: {k: None for k, _ in getters} for out in range(1, output_count + 1)
        }
        for key, getter in getters:
            outs = await asyncio.gather(
                *(_one(out, getter) for out in range(1, output_count + 1))
            )
            for out, val in outs:
                result[out][key] = val
        for out, state in result.items():
            state["error"] = None if all(state[k] is not None for k, _ in getters) else "partial"
        return result
