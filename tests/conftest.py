from hypothesis import HealthCheck, settings
import os

# Strict CI profile: heavy exploration for regression/CI
settings.register_profile(
    "ci",
    max_examples=200,
    deadline=200,
    suppress_health_check=[HealthCheck.too_slow],
    derandomize=False,
    print_blob=True,
)

# Light profile for mutation testing: faster per-mutant; still meaningful
settings.register_profile(
    "mutation",
    max_examples=25,          # 25–50 is a good band; raise if needed
    deadline=100,
    suppress_health_check=[HealthCheck.too_slow],
    derandomize=True,         # stable example sequence for reproducibility
)

# Default to CI unless caller overrides with HYPOTHESIS_PROFILE
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "ci"))