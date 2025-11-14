{
    'name': 'Product Register',
    'version': '1.0',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_register_views.xml',
        'views/product_register_import_views.xml',
    ],
    'installable': True,
}