import typer

from .nikon_z import enumerate_nikon_z_lens, read_nikon_z_lens


def main():
    for name, uri in enumerate_nikon_z_lens():
        spec = read_nikon_z_lens(name, uri)
        print("#", spec)


if __name__ == "__main__":
    typer.run(main)
