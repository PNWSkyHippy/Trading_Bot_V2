"""Track stock counts for a small warehouse."""


def restock(items, name, quantity):
    """Add stock for an item and return its new count.

    Args:
        items (dict[str, int]): Stock counts by item name, updated in place.
        name (str): Name of the item to restock.
        quantity (int): Number of units to add. Must be positive.

    Returns:
        int: The item's updated stock count.

    Raises:
        ValueError: If quantity is zero or negative.
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    items[name] = items.get(name, 0) + quantity
    return items[name]

def low_stock(items, threshold=5):
    """Return the names of items at or below the threshold.

    Args:
        items (dict[str, int]): Stock counts by item name.
        threshold (int): Highest count that counts as low stock. Defaults to 5.

    Returns:
        list[str]: Names of items whose count is at or below the threshold.
    """
    return [name for name, count in items.items() if count <= threshold]

class Warehouse:
    """Hold stock counts for one warehouse location."""

    def __init__(self, location):
        """Create an empty warehouse at the given location.

        Args:
            location (str): Where the warehouse is.
        """
        self.location = location
        self.items = {}

    def receive(self, name, quantity):
        """Receive a shipment of an item and return its new count.

        Args:
            name (str): Name of the item received.
            quantity (int): Number of units received. Must be positive.

        Returns:
            int: The item's updated stock count.

        Raises:
            ValueError: If quantity is zero or negative.
        """
        return restock(self.items, name, quantity)

