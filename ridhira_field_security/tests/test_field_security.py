from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError
from lxml import etree

class TestFieldSecurityV2(TransactionCase):

    def setUp(self):
        super().setUp()
        
        self.test_group = self.env['res.groups'].create({'name': 'Test Group'})
        user_vals = {
            'name': 'Test User V2',
            'login': 'test_user_v2',
        }
        group_field = 'group_ids' if 'group_ids' in self.env['res.users']._fields else 'groups_id'
        user_vals[group_field] = [(4, self.test_group.id), (4, self.env.ref('base.group_user').id)]
        self.test_user = self.env['res.users'].create(user_vals)
        
        self.partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        self.phone_field = self.env['ir.model.fields'].search([
            ('model_id', '=', self.partner_model.id),
            ('name', '=', 'phone')
        ], limit=1)

    def test_01_button_hiding(self):
        """Test that a button can be hidden using button_name target."""
        self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'target_type': 'button',
            'button_name': 'action_test_button',
            'group_ids': [(4, self.test_group.id)],
            'rule_type': 'invisible'
        })
        
        arch_str = '<form><button name="action_test_button" type="object" string="Test"/></form>'
        arch_node = etree.fromstring(arch_str)
        
        self.env['res.partner'].with_user(self.test_user)._apply_field_security_rules_to_arch(arch_node, 'form')
        
        button_node = arch_node.xpath('//button[@name="action_test_button"]')[0]
        self.assertEqual(button_node.get('invisible'), '1', "Button should be invisible")

    def test_02_exclude_behavior(self):
        """Test that exclude logic applies to users NOT in the group."""
        self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'target_type': 'field',
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.env.ref('base.group_erp_manager').id)], # Apply to all EXCEPT Admin
            'apply_behavior': 'exclude',
            'rule_type': 'readonly'
        })
        
        # test_user is not an admin, so it should be excluded and thus the rule applies
        fields_info = self.env['res.partner'].with_user(self.test_user).fields_get(allfields=['phone'])
        self.assertTrue(fields_info.get('phone', {}).get('readonly'), "Phone should be readonly for non-admin")
        
        # admin should not have the rule applied
        admin_fields = self.env['res.partner'].fields_get(allfields=['phone'])
        self.assertFalse(admin_fields.get('phone', {}).get('readonly', False), "Phone should not be readonly for admin")

    def test_03_view_type_granularity(self):
        """Test that a rule only applies to the specific view type."""
        # Test with modern Odoo list view_type
        rule_list = self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.test_group.id)],
            'view_type': 'list',
            'rule_type': 'invisible'
        })
        
        # Form view should NOT be modified
        arch_str = '<form><field name="phone"/></form>'
        arch_node = etree.fromstring(arch_str)
        self.env['res.partner'].with_user(self.test_user)._apply_field_security_rules_to_arch(arch_node, 'form')
        self.assertIsNone(arch_node.xpath('//field[@name="phone"]')[0].get('invisible'))
        
        # List view SHOULD be modified
        list_arch_str = '<list><field name="phone"/></list>'
        list_node = etree.fromstring(list_arch_str)
        self.env['res.partner'].with_user(self.test_user)._apply_field_security_rules_to_arch(list_node, 'list')
        self.assertEqual(list_node.xpath('//field[@name="phone"]')[0].get('invisible'), '1')
        rule_list.unlink()

        # Test backward compatibility with legacy tree view_type
        rule_tree = self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.test_group.id)],
            'view_type': 'tree',
            'rule_type': 'invisible'
        })
        tree_node = etree.fromstring(list_arch_str)
        self.env['res.partner'].with_user(self.test_user)._apply_field_security_rules_to_arch(tree_node, 'list')
        self.assertEqual(tree_node.xpath('//field[@name="phone"]')[0].get('invisible'), '1')
        rule_tree.unlink()

    def test_04_no_export_protection(self):
        """Test that no_export rule blocks the field from exportable metadata and export_data."""
        rule = self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.test_group.id)],
            'rule_type': 'no_export'
        })
        
        fields_info = self.env['res.partner'].with_user(self.test_user).fields_get(allfields=['phone'])
        self.assertFalse(fields_info.get('phone', {}).get('exportable', True), "Phone field should have exportable=False")

        # Test export_data filtering
        partner = self.env['res.partner'].create({'name': 'Test Partner Export', 'phone': '1234567890'})
        export_res = partner.with_user(self.test_user).export_data(['name', 'phone'])
        exported_cols = export_res.get('datas', [[]])[0]
        # 'phone' should be stripped from exported columns for unauthorized user
        self.assertEqual(len(exported_cols), 1, "Only 'name' should be exported; 'phone' must be blocked.")
        rule.unlink()

    def test_05_target_validation(self):
        """Test that required fields are enforced per target_type."""
        with self.assertRaises((ValidationError, Exception)):
            self.env['field.security.rule'].create({
                'model_id': self.partner_model.id,
                'target_type': 'field',
                'field_id': False,
            })
        with self.assertRaises((ValidationError, Exception)):
            self.env['field.security.rule'].create({
                'model_id': self.partner_model.id,
                'target_type': 'button',
                'button_name': False,
            })
        with self.assertRaises((ValidationError, Exception)):
            self.env['field.security.rule'].create({
                'model_id': self.partner_model.id,
                'target_type': 'page',
                'page_name': False,
            })

    def test_06_server_side_write_protection(self):
        """Test that server-side write is blocked at the ORM level when enforce_backend is enabled."""
        rule = self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'target_type': 'field',
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.test_group.id)],
            'rule_type': 'readonly',
            'enforce_backend': True,
        })
        
        partner = self.env['res.partner'].create({'name': 'Test Partner', 'phone': '1111111111'})
        
        # Test write raises AccessError for unauthorized user
        with self.assertRaises(AccessError):
            partner.with_user(self.test_user).write({'phone': '9999999999'})
            
        # Admin can still write without restriction
        partner.write({'phone': '2222222222'})
        self.assertEqual(partner.phone, '2222222222')
        rule.unlink()

    def test_07_data_masking(self):
        """Test that confidential data is masked in read() operations."""
        rule = self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'target_type': 'field',
            'field_id': self.phone_field.id,
            'group_ids': [(4, self.test_group.id)],
            'rule_type': 'mask',
            'masking_pattern': 'partial_end'
        })
        
        partner = self.env['res.partner'].create({'name': 'Secret Client', 'phone': '9876543210'})
        
        # Test user reading phone should see masked data
        read_res = partner.with_user(self.test_user).read(['name', 'phone'])
        self.assertTrue(read_res[0]['phone'].endswith('3210'), "Phone should end with unmasked digits")
        self.assertTrue('*' in read_res[0]['phone'], "Phone should contain asterisks")
        
        # Admin reading phone gets unmasked data
        admin_read = partner.read(['name', 'phone'])
        self.assertEqual(admin_read[0]['phone'], '9876543210')
        rule.unlink()

    def test_08_tab_page_hiding(self):
        """Test that an entire notebook page/tab is hidden via arch modification."""
        rule = self.env['field.security.rule'].create({
            'model_id': self.partner_model.id,
            'target_type': 'page',
            'page_name': 'internal_notes',
            'group_ids': [(4, self.test_group.id)],
            'rule_type': 'invisible'
        })
        
        arch_str = (
            '<form><notebook>'
            '<page name="internal_notes" string="Internal Notes"><field name="comment"/></page>'
            '<page name="public_info" string="Public"><field name="name"/></page>'
            '</notebook></form>'
        )
        arch_node = etree.fromstring(arch_str)
        self.env['res.partner'].with_user(self.test_user)._apply_field_security_rules_to_arch(arch_node, 'form')
        
        page_node = arch_node.xpath('//page[@name="internal_notes"]')[0]
        self.assertEqual(page_node.get('invisible'), '1', "Internal Notes tab should be marked invisible")
        
        public_node = arch_node.xpath('//page[@name="public_info"]')[0]
        self.assertIsNone(public_node.get('invisible'), "Public tab should remain visible")
        rule.unlink()
