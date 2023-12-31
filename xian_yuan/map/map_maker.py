import csv
import json

if __name__ == "__main__":
    map_list = []
    with open('map.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        x = 0
        y = 0
        for row in reader:
            for col in row:
                if col != "" and col != '\ufeff':
                    item = {
                        "name": col,
                        "coordinate": [x, y]
                    }
                    map_list.append(item)

                y += 1
            x += 1
    print(json.dumps(map_list))
