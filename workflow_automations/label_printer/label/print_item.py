"""Step 3 checkpoint: pull one real item and print its full label set.

Usage: python label/print_item.py <item_id>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monday.client import list_active_requests_items, get_item_fields
from label.render import build_labels_for_item
from printer.send import print_images


def print_item(item_id: str):
    fields = get_item_fields(item_id)
    labels = build_labels_for_item(fields)
    print(f"{fields['name']}: printing {len(labels)} label(s) "
          f"({fields['n_samples']} numbered + {len(fields['add_samples'])} additional: {fields['add_samples']})")
    results = print_images(labels)
    for idx, result in enumerate(results, start=1):
        print(f"  [{idx}/{len(labels)}] sent -> {result}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_id = sys.argv[1]
    else:
        items = list_active_requests_items()
        if not items:
            print("No items in Active Requests.")
            sys.exit(1)
        print("No item_id given, using first item in Active Requests:")
        for item in items:
            print(f"  {item['id']}  {item['name']}")
        target_id = items[0]["id"]

    print_item(target_id)
