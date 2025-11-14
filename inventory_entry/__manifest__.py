{
    'name': 'Inventory Entries',
    'version': '1.0',
    'depends': ['base', 'product_register'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_entry_views.xml',
        'views/inventory_movement_views.xml',
    ],
    'installable': True,
}