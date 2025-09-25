from abc import ABC, abstractmethod

class Transport(ABC):
    """
    Abstract base class for all Transport implementations.
    Defines the interface for opening, sending data, and closing transports.
    """

    @abstractmethod
    async def open(self) -> None:
        """
        Initialize and open the transport (e.g., start listeners or connections).
        """
        raise NotImplementedError

    @abstractmethod
    async def send(self, msg: bytes, address: str) -> None:
        """
        Send a message over the transport to the given address.

        :param msg: The raw bytes to send.
        :param address: A transport-specific identifier (e.g., port name or IP address).
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """
        Gracefully close the transport and clean up resources.
        """
        raise NotImplementedError

    @abstractmethod
    async def handle_conn(self, *args, **kwargs)-> None:
        raise NotImplementedError
