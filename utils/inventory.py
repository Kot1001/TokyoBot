import math


__all__ = (
    'stack',
)


def stack(size, count, stack_size):
    # TODO: Сделать чтобы оно также возвращало количество стаков (и соответственно добавить отображение этого)
    return {
        'occupied_space': math.ceil(size * count / stack_size) * size,
        'stack_count': ...
    }
