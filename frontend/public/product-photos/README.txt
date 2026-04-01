Add real product images here.

How to use:
- Put your product photos in this folder.
- In backend/app/data/products.json, set:
  "image": "your-file-name.jpg"
  "gallery": ["your-file-name-2.jpg", "your-file-name-3.jpg"]

Examples:
- "image": "nova-x5-pro-front.jpg"
- "gallery": ["nova-x5-pro-back.jpg", "nova-x5-pro-side.jpg"]

You can also use nested paths like:
- "image": "phones/nova-x5-pro/front.jpg"

The frontend will automatically read them from:
- /product-photos/...
