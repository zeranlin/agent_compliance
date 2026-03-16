from setuptools import find_packages, setup


setup(
    name="agent-compliance",
    version="0.1.0",
    description="Local government procurement compliance review harness",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "agent-compliance=agent_compliance.cli:main",
        ]
    },
)
