#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查当前数据库状态"""
import sys, os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

from framework.database import db
db.init()

users = db.get_users()
print("USERS:")
for u in users:
    uname = u.get("username") or "-"
    print("  id=%d name=%s role=%s username=%s" % (u["id"], u["name"], u["role"], uname))

admins = db.get_admins()
print("ADMINS:")
for a in admins:
    print("  id=%d username=%s display_name=%s" % (a["id"], a["username"], a.get("display_name", "")))

classes = db.get_classes()
print("CLASSES:")
for c in classes:
    print("  id=%d name=%s teacher_id=%s" % (c["id"], c["name"], c.get("teacher_id", "")))

print("Total: %d users, %d admins, %d classes" % (len(users), len(admins), len(classes)))

reports = db.get_learning_reports(limit=20)
print("LEARNING REPORTS: %d" % len(reports))
for r in reports[:5]:
    topic = (r.get("topic") or "")[:30]
    print("  id=%d user_id=%d topic=%s score=%s" % (r["id"], r["user_id"], topic, r.get("score", 0)))

# check schools/grades
schools = db.get_schools()
print("SCHOOLS: %d" % len(schools))
grades = db.get_grades()
print("GRADES: %d" % len(grades))
