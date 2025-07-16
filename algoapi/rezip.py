import shutil
updated_zip_path = "/mnt/data/algoapi_dockerized.zip"

# Create a ZIP file of the updated algoapi folder
shutil.make_archive(updated_zip_path.replace(".zip", ""), 'zip', "/mnt/data/algoapi")

updated_zip_path