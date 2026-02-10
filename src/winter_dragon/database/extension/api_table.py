"""Extension for databases, integrating api's with the database layer."""

from abc import abstractmethod
from typing import Any, ClassVar, Required, Self, TypedDict, Unpack

import requests
from pydantic import ConfigDict

from .model import SQLModel


class ApiArguments(TypedDict):
    """Required arguments for API calls."""

    api_key: Required[str]


class ApiTable(SQLModel, table=True):
    """Base class for API-related tables.

    This can be extended to create specific tables for different APIs,
    ensuring a consistent structure and integration with the database.
    """

    __abstract__ = True  # This is an abstract base class, not a table itself

    base_url: ClassVar[str]
    route: ClassVar[str]
    required_params: ClassVar[ApiArguments]
    fields: ClassVar[dict[str, Any]] = {}

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]) -> None:
        """Set the table name based on the class name."""
        super().__init_subclass__(**kwargs)
        parent = next(i for i in cls.mro() if issubclass(i, ApiTable) and i is not ApiTable)

        cls.__tablename__ = parent.__tablename__ + cls.__name__.lower()

    def fetch(self, **kwargs: Unpack[ApiArguments]) -> Self:
        """Fetch data from the API and store it in the database.

        This method should be implemented by subclasses to perform the actual API call,
        validate required parameters, and handle data storage.

        Args:
            **kwargs: Required parameters for the API call, as defined in `required_params`.

        """
        missing_params = [param for param in self.required_params if param not in kwargs]
        if missing_params:
            msg = f"Missing required parameters: {', '.join(missing_params)} for <{self.__class__.__name__}>"
            raise ValueError(msg)
        result: Self = self.make_api_call(**kwargs)
        result.add()
        return result

    @classmethod
    def make_api_call(cls, **params: Unpack[ApiArguments]) -> Self:
        """Make the actual API call.

        Performs an HTTP GET request to the API endpoint and parses the JSON response
        according to the fields defined in cls.fields.
        """
        url = f"{cls.base_url}{cls.route}"
        cls.logger.debug(f"Making API call to: {url} with params: {params}")
        response = cls._get_response(url)
        return cls(**cls._parse_api_response(response.json()))

    @classmethod
    def _parse_api_response(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Parse the API response and extract fields based on cls.fields."""
        extracted_data = {}
        for field_name in cls.fields:
            if field_name in data:
                extracted_data[field_name] = data[field_name]
            else:
                cls.logger.warning(f"Field '{field_name}' not found in API response")
        return extracted_data

    @abstractmethod
    @classmethod
    def get_headers(cls) -> dict[str, str]:
        """Get headers for the API request.

        This method should be implemented by subclasses to provide necessary headers,
        such as authentication tokens.
        """

    @classmethod
    def _get_response(cls, url: str) -> requests.Response:
        response = requests.get(url, headers=cls.get_headers(), timeout=10)
        response.raise_for_status()
        return response

    def validate(self) -> None:  # pyright: ignore[reportIncompatibleMethodOverride] # ty:ignore[invalid-method-override]  BaseModel.validate from pydantic is deprecated. We can use it as we require for validation of required parameters.
        """Validate that all required parameters are set."""
        missing_params = [param for param in self.required_params if not hasattr(self, param) or getattr(self, param) is None]
        if missing_params:
            msg = f"Missing required parameters: {', '.join(missing_params)} for <{self.__class__.__name__}>"
            raise ValueError(msg)


# Example usage:


class RiotClashV1(ApiTable):
    """Table for storing Riot Clash API endpoints and parameters."""

    base_url = "https://euw1.api.riotgames.com/lol/clash/v1/"


class RiotTournaments(RiotClashV1, table=True):
    """Table for storing Riot Tournaments API endpoints and parameters."""

    route = "tournaments"
    fields: ClassVar[dict[str, Any]] = {
        "id": int,
        "registrationTime": int,
        "startTime": int,
        "cancelled": bool,
    }
