"""Redis configuration and connection management."""

from __future__ import annotations

import asyncio
import os
from inspect import isawaitable

from herogold.log.logging import getLogger

from redis import ConnectionPool, Redis
from winter_dragon.config import Config


class RedisConfig:
    """Redis configuration settings.

    Environment variables take precedence over config.ini values.
    Useful for Docker deployments where host needs to be 'redis' instead of 'localhost'.
    """

    _host = Config("localhost")
    _port = Config(6379)
    _db = Config(0)
    _password = Config("")
    decode_responses = Config(default=True)
    socket_connect_timeout = Config(5)
    socket_timeout = Config(5)

    @staticmethod
    def get_host() -> str:
        """Get Redis host, preferring environment variable over config."""
        return os.getenv("REDIS_HOST") or RedisConfig._host

    @staticmethod
    def get_port() -> int:
        """Get Redis port, preferring environment variable over config."""
        env_port = os.getenv("REDIS_PORT")
        return int(env_port) if env_port else RedisConfig._port

    @staticmethod
    def get_db() -> int:
        """Get Redis database, preferring environment variable over config."""
        env_db = os.getenv("REDIS_DB")
        return int(env_db) if env_db else RedisConfig._db

    @staticmethod
    def get_password() -> str:
        """Get Redis password, preferring environment variable over config."""
        return os.getenv("REDIS_PASSWORD") or RedisConfig._password


logger = getLogger("RedisConnection")


class RedisConnection:
    """Redis connection manager with singleton pattern."""

    _instance: Redis | None = None
    _pool: ConnectionPool | None = None
    _rq_instance: Redis | None = None
    _rq_pool: ConnectionPool | None = None

    @classmethod
    def get_connection(cls, *, decode_responses: bool | None = None) -> Redis:
        """Get or create Redis connection.

        Args:
            decode_responses: Override decode_responses setting.
                            None uses config default (True).
                            False required for RQ (binary/pickled data).

        Returns:
            Redis: Redis client instance

        """
        # Use separate connections for RQ (binary) and regular (decoded) operations
        if decode_responses is False:
            if cls._rq_instance is None:
                cls._rq_instance = cls._create_connection(decode_responses=False)
            return cls._rq_instance
        if cls._instance is None:
            cls._instance = cls._create_connection(decode_responses=decode_responses)
        return cls._instance

    @classmethod
    def _create_connection(cls, *, decode_responses: bool | None = None) -> Redis:
        """Create a new Redis connection with connection pooling.

        Args:
            decode_responses: Override decode_responses setting.
                            None uses config default.

        Returns:
            Redis: Configured Redis client

        """
        should_decode = decode_responses if decode_responses is not None else RedisConfig.decode_responses

        logger.info(
            f"Creating Redis connection to {RedisConfig.get_host()}:{RedisConfig.get_port()} "
            f"db={RedisConfig.get_db()} decode_responses={should_decode}"
        )

        # Create connection pool with appropriate decode setting
        pool = ConnectionPool(
            host=RedisConfig.get_host(),
            port=RedisConfig.get_port(),
            db=RedisConfig.get_db(),
            password=RedisConfig.get_password() or None,
            decode_responses=should_decode,
            socket_connect_timeout=RedisConfig.socket_connect_timeout,
            socket_timeout=RedisConfig.socket_timeout,
            max_connections=50,
        )

        # Store the pool in the appropriate variable
        if decode_responses is False:
            cls._rq_pool = pool
        else:
            cls._pool = pool

        # Create Redis client from pool
        client = Redis(connection_pool=pool)

        try:
            # Test connection
            client.ping()
            logger.info("Redis connection established successfully")
        except ConnectionError:
            logger.exception("Failed to connect to Redis:")
            raise

        return client

    @classmethod
    def close_connection(cls) -> None:
        """Close Redis connection and cleanup resources."""
        if cls._instance:
            try:
                cls._instance.close()
                logger.info("Redis connection closed")
            except Exception:
                logger.exception("Error closing Redis connection:")
            finally:
                cls._instance = None

        if cls._rq_instance:
            try:
                cls._rq_instance.close()
                logger.info("Redis RQ connection closed")
            except Exception:
                logger.exception("Error closing Redis RQ connection:")
            finally:
                cls._rq_instance = None

        if cls._pool:
            try:
                cls._pool.disconnect()
                logger.info("Redis connection pool disconnected")
            except Exception:
                logger.exception("Error disconnecting Redis pool:")
            finally:
                cls._pool = None

        if cls._rq_pool:
            try:
                cls._rq_pool.disconnect()
                logger.info("Redis RQ pool disconnected")
            except Exception:
                logger.exception("Error disconnecting Redis RQ pool:")
            finally:
                cls._rq_pool = None

    @classmethod
    def test_connection(cls) -> bool:
        """Test if Redis connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise

        """
        try:
            client = cls.get_connection()
            ping = client.ping()
            if isawaitable(ping):
                return asyncio.get_event_loop().run_until_complete(ping)
        except Exception:
            logger.exception("Redis health check failed:")
            return False
        else:
            return ping
