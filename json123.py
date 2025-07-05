# import json

# with open("sanpham.json", "r", encoding="utf-8") as f:
#     data = json.load(f)

# with open("shopping_assistant.sql", "a", encoding="utf-8") as out:
#     out.write("\n\n-- Insert product data\n")
#     out.write("INSERT INTO products (id, title, price, description, category, image, rating_rate, rating_count) VALUES\n")

#     for i, item in enumerate(data):
#         values = (
#             item["id"],
#             item["title"].replace("'", "''"),
#             item["price"],
#             item["description"].replace("'", "''"),
#             item["category"],
#             item["image"],
#             item["rating"]["rate"],
#             item["rating"]["count"]
#         )
#         line = f"({values[0]}, '{values[1]}', {values[2]}, '{values[3]}', '{values[4]}', '{values[5]}', {values[6]}, {values[7]})"
#         out.write(line)
#         out.write(",\n" if i < len(data) - 1 else ";\n")
