print('Równanie w postaci a*x**2 + b*x + c == 0')
a = input('Podaj a ')
a = float(a)
b = input('Podaj b ')
b = float(b)
c = input('Podaj c ')
c = float(c)
delta = (b**2) - (4 * a * c)
delta = float(delta)
x_1 = (-b - delta**0.5) / (2 * a)
x_2 = (-b + delta**0.5) / (2 * a)
if delta > 0:
    print(f'x_1 = {x_1}')
    print(f'x_2 = {x_2}')
elif delta == 0:
    print(f'x_1 = x_2 = {x_1}')
else:
    print('brak rozwiązań')
