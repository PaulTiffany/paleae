from hypothesis import HealthCheck, settings

settings.register_profile(
    "ci",
    max_examples=200,
    deadline=200,
    suppress_health_check=[HealthCheck.too_slow],
    derandomize=False,
    print_blob=True,
)
settings.load_profile("ci")
