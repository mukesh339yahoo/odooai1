{
    'name': 'Advanced Field-Level Security & UI Manager',
    'version': '20.0.1.0.0',
    'category': 'Administration/Security',
    'summary': 'Dynamic Field Security, Hide Tabs/Buttons, Data Masking & Server-Side Write Protection without code',
    'description': """
Advanced Field-Level Security & UI Manager for Odoo 20
======================================================
The most complete, no-code access management suite for Odoo.

Key Highlights:
---------------
* **Field Security:** Make fields Invisible, Read-Only, or Required dynamically.
* **True Server-Side Protection:** Restricts backend write/create/import operations at the ORM level, preventing developer mode or API tampering.
* **Confidential Data Masking:** Obfuscate sensitive fields (salaries, phone numbers, bank accounts) with full or partial masks (e.g. **** 1234).
* **Notebook Tab / Page Hiding:** Dynamically hide entire form view notebook pages and tabs based on user groups or record conditions.
* **Button & Action Hiding:** Prevent unauthorized workflow executions by hiding specific action buttons.
* **Export Protection:** Prevent data leakage by blocking sensitive fields from Excel and CSV exports.
* **Multi-Company Compatible:** Apply rules globally or selectively per company.
* **Dynamic Domain Conditions:** Conditional security based on record states (e.g., state == 'done').
* **Rule Priority Ordering:** Drag-and-drop sequence management for fine-grained rule inheritance.
    """,
    'author': 'Ridhira Technologies, Pune, India',
    'website': 'https://ridhira.desigoogly.com',
    'images': ['static/description/screenshot_1.png'],
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/field_security_rule_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
