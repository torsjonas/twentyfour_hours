
points = []
points.append([10,6])
points.append([5,4])
points.append([10,4,4])

sum = 0

for point in points:
    if len(point) == 2:
        sum += (point[0] + point[1]) / 2
    if len(point) == 3:
        sum += (point[0] + point[1] + point[2]) / 3


print(sum)

total = 0

for point in points:
    if len(point) == 2:
        total += (point[0] + point[1])
    if len(point) == 3:
        total += (point[0] + point[1] + point[2])

print(total)
print(total / 7)
