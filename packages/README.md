# Packages

Reusable monorepo capabilities live here. Dependency direction is domain → application → infrastructure from inner to outer use; imports must point inward. Each package publishes its interface through `__init__.py` and documents responsibility and dependencies in its README.
