import tifffile

def create_hyperstack_olympus(
    image_path: str
):
    if image_path.endswith(".oif"):
        image = tifffile.imread(image_path, is_ome=True)
        return image