# wd-types

Cross-package structural types: the `Mentionable` protocol and generic aliases (`Store[T]`, `MaybeAwaitable[T]`, `CoroutineFunction`, `MaybeAwaitableFunc`).

The clock lives here too: `wd_types.clock.utc_now` is the only way to get "now". Don't call `datetime.now(UTC)` or write a local `utc_now`; import this one (into the module namespace, so tests can `monkeypatch.setattr(module, "utc_now", ...)`).

- **Depends on:** nothing internal. Put a type here when two packages need it and neither should import the other.
- **API reference:** [wd_types](../docs/reference/wd-types.md)
