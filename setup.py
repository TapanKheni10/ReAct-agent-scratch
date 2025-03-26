import setuptools

with open("README.md", "r", encoding="utf-8") as f:
    long_discription = f.read()

__version__ = "0.0.1"

REPO_NAME = "ReAct-agent-scratch"
AUTHOR_USER_NAME = "TapanKheni10"
AUTHOR_EMAIL = "tapankheni10304@gmail.com"
SRC_REPO = "src"

setuptools.setup(
    name=SRC_REPO,
    version=__version__,
    author=AUTHOR_USER_NAME,
    author_email=AUTHOR_EMAIL,
    description="A package for meeting management",
    long_description=long_discription,
    long_description_content_type="text/markdown",
    url=f"https://github.com/{AUTHOR_USER_NAME}/{REPO_NAME}",
    project_urls={
        "Bug Tracker": f"https://github.com/{AUTHOR_USER_NAME}/{REPO_NAME}/issues"
    },
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    
)

