import logging
from lxml import etree
from odoo import models, api
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_applicable_security_rules(self, target_types=None, view_type=None):
        """Retrieve active field security rules applicable to the current user and model."""
        if self.env.is_superuser() or self.env.su:
            return self.env['field.security.rule']

        company_id = self.env.company.id if hasattr(self.env, 'company') else False
        domain = [('model_id.model', '=', self._name)]
        if company_id:
            domain.extend(['|', ('company_id', '=', False), ('company_id', '=', company_id)])

        if target_types:
            domain.append(('target_type', 'in', target_types))

        rules = self.env['field.security.rule'].sudo().search(domain, order='sequence, id')
        if not rules:
            return self.env['field.security.rule']

        user = self.env.user
        user_groups = getattr(user, 'group_ids', getattr(user, 'groups_id', self.env['res.groups']))

        matched_rule_ids = []
        for rule in rules:
            # Check view type granularity
            if view_type and rule.view_type != 'all' and rule.view_type != view_type:
                if rule.view_type in ('tree', 'list') and view_type in ('tree', 'list'):
                    pass
                else:
                    continue

            # Check User / Group membership
            match = (user in rule.user_ids) or bool(user_groups & rule.group_ids)

            if rule.apply_behavior == 'include' and match:
                matched_rule_ids.append(rule.id)
            elif rule.apply_behavior == 'exclude' and not match:
                matched_rule_ids.append(rule.id)

        return self.env['field.security.rule'].browse(matched_rule_ids)

    @api.model
    def _apply_field_security_rules_to_arch(self, arch_node, view_type):
        """Inject XML modifiers into the view architecture for fields, buttons, and notebook tabs."""
        applied_rules = self._get_applicable_security_rules(
            target_types=['field', 'button', 'page'],
            view_type=view_type
        )
        if not applied_rules:
            return

        rules_by_field = {}
        rules_by_button = {}
        rules_by_page = []

        for rule in applied_rules:
            if rule.target_type == 'field' and rule.field_id:
                rules_by_field.setdefault(rule.field_id.name, []).append(rule)
            elif rule.target_type == 'button' and rule.button_name:
                rules_by_button.setdefault(rule.button_name, []).append(rule)
            elif rule.target_type == 'page' and rule.page_name:
                rules_by_page.append(rule)

        # 1. Apply rules to fields
        for node in arch_node.xpath('//field'):
            field_name = node.get('name')
            if field_name in rules_by_field:
                for rule in rules_by_field[field_name]:
                    self._inject_rule_modifier(node, rule)

        # 2. Apply rules to buttons
        for node in arch_node.xpath('//button'):
            button_name = node.get('name')
            if button_name in rules_by_button:
                for rule in rules_by_button[button_name]:
                    self._inject_rule_modifier(node, rule)

        # 3. Apply rules to notebook tabs / pages
        if rules_by_page:
            for node in arch_node.xpath('//page'):
                p_name = (node.get('name') or '').strip().lower()
                p_string = (node.get('string') or '').strip().lower()
                for rule in rules_by_page:
                    target_p = rule.page_name.strip().lower()
                    if (p_name and p_name == target_p) or (p_string and p_string == target_p):
                        self._inject_rule_modifier(node, rule)

    def _inject_rule_modifier(self, node, rule):
        """Set or combine dynamic modifiers (invisible, readonly, required) on an XML node."""
        modifier = rule.rule_type
        if modifier in ('no_export', 'mask'):
            # Data-protection rules that do not affect UI node attributes directly
            return

        value = rule.domain or '1'
        existing_val = node.get(modifier)
        if existing_val and value != '1' and existing_val != '1' and existing_val != '0':
            node.set(modifier, f"({existing_val}) or ({value})")
        else:
            node.set(modifier, value)

        if modifier == 'readonly' and node.get('force_save') is None:
            node.set('force_save', '1')

    def _check_field_security_write(self, vals):
        """Enforce server-side write and create protection against API / script tampering."""
        if not vals or self.env.is_superuser() or self.env.su:
            return
        if self.env.context.get('install_mode') or self.env.context.get('bypass_field_security'):
            return

        rules = self._get_applicable_security_rules(target_types=['field'])
        for rule in rules:
            if not rule.enforce_backend or not rule.field_id:
                continue
            fname = rule.field_id.name
            if fname in vals and rule.rule_type in ('readonly', 'invisible') and not rule.domain:
                fdesc = rule.field_id.field_description or fname
                model_desc = self._description or self._name
                raise AccessError(
                    f"Access Denied: You do not have permission to modify field '{fdesc}' on {model_desc}."
                )

    def write(self, vals):
        self._check_field_security_write(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_field_security_write(vals)
        return super().create(vals_list)

    def read(self, fields=None, load='_classic_read'):
        """Obfuscate confidential field values if data-masking rules apply."""
        res = super().read(fields=fields, load=load)
        if self.env.is_superuser() or self.env.su or not res:
            return res

        mask_rules = self._get_applicable_security_rules(target_types=['field']).filtered(
            lambda r: r.rule_type == 'mask' and r.field_id
        )
        if not mask_rules:
            return res

        for rule in mask_rules:
            fname = rule.field_id.name
            pattern = rule.masking_pattern or 'all'
            for record_dict in res:
                if fname in record_dict and record_dict[fname]:
                    raw_val = str(record_dict[fname])
                    val_len = len(raw_val)
                    if pattern == 'partial_end':
                        masked = ('*' * max(val_len - 4, 3)) + raw_val[-4:] if val_len > 4 else '****'
                    elif pattern == 'partial_start':
                        masked = raw_val[:4] + ('*' * max(val_len - 4, 3)) if val_len > 4 else '****'
                    else:
                        masked = '********'
                    record_dict[fname] = masked

        return res

    def export_data(self, fields_to_export):
        """Prevent sensitive or non-exportable fields from being exported to Excel or CSV."""
        if not self.env.is_superuser() and not self.env.su:
            restricted_rules = self._get_applicable_security_rules(target_types=['field']).filtered(
                lambda r: (r.rule_type in ('no_export', 'invisible') and not r.domain)
            )
            if restricted_rules:
                blocked_fields = {r.field_id.name for r in restricted_rules if r.field_id}
                fields_to_export = [
                    f for f in fields_to_export
                    if f.split('/')[0] not in blocked_fields and f not in blocked_fields
                ]
        return super().export_data(fields_to_export)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)

        try:
            arch_raw = res.get('arch') if isinstance(res, dict) else None
            if arch_raw is not None:
                if isinstance(arch_raw, str):
                    arch_node = etree.fromstring(arch_raw)
                    self._apply_field_security_rules_to_arch(arch_node, view_type)
                    res['arch'] = etree.tostring(arch_node, encoding='unicode')
                else:
                    self._apply_field_security_rules_to_arch(arch_raw, view_type)
        except Exception as e:
            _logger.error("Failed to apply field security rules on %s: %s", self._name, e)

        return res

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)

        if self.env.is_superuser() or self.env.su or not res:
            return res

        rules = self._get_applicable_security_rules(target_types=['field'])
        for rule in rules:
            if not rule.field_id:
                continue
            field_name = rule.field_id.name
            if field_name in res:
                if rule.rule_type == 'invisible' and not rule.domain:
                    res.pop(field_name, None)
                elif rule.rule_type == 'readonly' and not rule.domain:
                    res[field_name]['readonly'] = True
                elif rule.rule_type == 'required' and not rule.domain:
                    res[field_name]['required'] = True
                elif rule.rule_type == 'no_export':
                    res[field_name]['exportable'] = False

        return res
