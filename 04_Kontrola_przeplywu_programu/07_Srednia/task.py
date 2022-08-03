numbers = []
n = input('podaj n: ')
n = int(n)
for num in range(n):
    num_1 = input('Podaj liczbę: ')
    num_1 = str(num_1)
    numbers.append(num_1)
    numbers_1 = (' '.join(numbers))
    numbers_1 = str(numbers_1)
    Sum = sum(map(int, numbers))
    avg = Sum / len(numbers)
print(f'Wprowadzone liczby: {numbers_1}')
print(f'Suma: {Sum},')
print(f'Średnia: {avg}')

if Sum > avg:
    print('Suma jest większa!')
else:
    print('Średnia jest większa')
