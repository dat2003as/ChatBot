import os
from typing import Any
from dotenv import load_dotenv

load_dotenv()


class Env:
    @staticmethod
    def get(var_name: str, default_val: str | None = None) -> str | None:
        val = os.environ.get(var_name)
        if val is not None:
            return val
        return default_val

    @staticmethod
    def get_required(var_name: str) -> str:
        val = os.environ.get(var_name)
        if val is None:
            raise RuntimeError(f"env {var_name} must be set")
        return val

    @staticmethod
    def aasert_of(
        exp: Any, on_success_msg: str | None = None, on_failure_msg: str | None = None
    ):
        if not exp:
            on_failure_msg = on_failure_msg or "assert failed"
            print(on_failure_msg)
            raise AssertionError(on_failure_msg)
        if on_success_msg:
            print(on_success_msg)
