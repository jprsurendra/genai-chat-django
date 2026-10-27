'''
Pydantic schemas essentially define the data structure (DTOs), so they should be placed in a `dtos` folder.
1. `models/db_models.py` defines the database structure. In Django, whenever a `models` folder or a `models.py` file is created, Django’s ORM (Object-Relational Mapper) scans it. Django expects to find classes that inherit from `django.db.models.Model` (such as `User`, `Product`, or `ChatSession`).

2. If you were to place Pydantic classes—which are used to validate API data—in that same location, Django’s ORM would attempt to process them and become confused.

It is essential to maintain a clear distinction between `django.db.models` and Pydantic.

Keeping them separate ensures that Django’s ORM (database layer) and Pydantic’s validation logic do not conflict with one another.


schemas.py (Pydantic) = "Data Transfer Objects (DTOs)". This simply defines the structure of the JSON data being sent to or received from the internet (API). It has nothing to do with the database.

models.py (Django) = "Database Tables". This defines what the tables in the database will look like.

'''

"""
This package exposes Pydantic schemas (DTOs) for use across the application.
"""
from .schemas import ChatMessage, ChatRequest, ChatResponse


'''
🎓 Educational Note:
Why the folder name `dtos`? Because it clearly indicates that these files are used to transfer data from one place to another (Data Transfer Objects).

Why the filename `schemas.py`? Because in Pydantic, these classes are referred to as "schemas," as they define the structure (or "shape") of the data. This naming convention is very common among developers.
'''