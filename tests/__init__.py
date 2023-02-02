from io import BytesIO
import tarfile
import requests


def download_data():
    print("Downloading ...")
    request = requests.get(
        "https://github.com/gamecss/raws/raw/main/2301-navigraph_for_aerosoft_ONLY_FOR\
_TEST.tar.xz"
    )
    print("Extracting ...")
    with BytesIO(request.content) as io:
        tarfile.open(fileobj=io, mode="r:xz").extractall("/tmp/")


print()
download_data()
