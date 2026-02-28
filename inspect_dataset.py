from pprint import pprint
import lancedb

db = lancedb.connect("hf://datasets/lancedb/magical_kingdom")
table = db.open_table("characters")

versions = table.list_versions()
pprint(versions)

# # Read the first version of the table
# first_version = min(v["version"] for v in versions)  # oldest/first manifest version
# table.checkout(first_version)
# print(table.version)  # now reading old version

# # Restore the first version as the latest version
# # Creates a new latest version equal to first_version's data
# table.restore(first_version)
# print(table.version)
