"""The provider plane: platform admins, the tenants register, branding, provisioning.

Other modules reach tenancy through ``verity.modules.tenancy.service`` — never its
repository, models, or tables. The IAM module's two wiring points are
``TenancyService.use_gates`` (the membership checks provisioning asks for) and
``TenancyService.register_tenant`` (self-service signup builds on it).
"""
