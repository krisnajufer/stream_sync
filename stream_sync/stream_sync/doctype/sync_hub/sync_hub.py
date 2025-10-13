# Copyright (c) 2025, Jufer and contributors
# For license information, please see license.txt
import re
import json

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime
from frappe.utils.background_jobs import get_jobs

from stream_sync.stream_sync.doctype.stream_consumer.stream_consumer import get_consumer_site
from stream_sync.stream_sync.doctype.stream_update_log.stream_update_log import make_stream_update_log

class SyncHub(Document):
	@frappe.whitelist()
	def get_data(self):
		key = "item_code" if self.ref_doctype == "Item" else "name"
		consumer_doctype = frappe.db.get_all("Stream Consumer Doctype", filters={"ref_doctype": self.ref_doctype, "stream_type": "Manual"}, fields="*")
		
		documents = []
		for row in consumer_doctype:
			consumer_site = get_consumer_site(row.parent)

			filters, or_filters = parse_condition(row.condition)
			documents = get_new_data_producer(self.ref_doctype, consumer_site, key, filters, or_filters, documents)
			
			filters.update({
				"amended_from": ["is", "set"],
				"docstatus": 1
			})
			documents = get_outdated_docs(self.ref_doctype, consumer_site, filters, documents, row)

		return documents

def parse_condition(condition):
	"""Ubah string condition jadi filters dan or_filters untuk frappe.db.get_list"""
	if not condition:
		return {}, {}

	condition = condition.replace("doc.", "").strip()
	filters, or_filters = {}, {}

	if " or " in condition:
		parts = [p.strip() for p in condition.split(" or ")]
		target = or_filters
	else:
		parts = [p.strip() for p in condition.split(" and ")]
		target = filters

	for part in parts:
		m = re.match(r"(\w+)\s*(==|!=)\s*[\"']?([^\"']+)[\"']?", part)
		if m:
			field, op, val = m.groups()
			if val.isdigit():
				val = int(val)
			target[field] = [("=" if op == "==" else "!="), val]

	return filters, or_filters

def get_new_data_producer(doctype, consumer_site, key, filters, or_filters, documents):
	filters.update({"amended_from": ["is", "not set"]})
	producer_data = frappe.db.get_all(doctype, filters=filters, or_filters=or_filters, fields=["name"])

	filters.pop("docstatus")
	consumer_data = consumer_site.get_list(doctype, filters=filters, fields=["name"])

	name_sources = {i[key]: i for i in producer_data}
	name_targets = {i[key]: i for i in consumer_data}
	
	new_data = [name for name in name_sources if name not in name_targets]
	for new in new_data:
		documents.append({
			"document": new,
			"update_type": "Create"
		})

	return documents

def get_outdated_docs(doctype, consumer_site, filters, documents, consumer_doctype):
	"""Bandingkan dokumen yang di-amend di Producer dan Consumer.
	Jika consumer.modified < producer.modified → masukkan ke array hasil.
	"""

	producer_amended = frappe.get_all(
		doctype,
		filters=filters,
		fields=["name", "amended_from", "modified"]
	)

	for p_doc in producer_amended:
		doc = frappe.get_doc(doctype, p_doc.name)
		amended_from = check_amended_from(doc) if consumer_doctype.amend_mode == "Update Source" else p_doc.name
		consumer_doc = consumer_site.get_value(
			doctype,
			["name", "modified"],
			{"name" :amended_from}
		)
		
		if not consumer_doc:
			continue

		consumer_modified = get_datetime(consumer_doc["modified"])
		producer_modified = get_datetime(p_doc.modified)
	
		if consumer_modified < producer_modified:
			documents.append({
				"document": p_doc.name,
				"update_type": "Update"
			})

	return documents

def check_amended_from(doc):
	if doc.get('amended_from'):
		amend_doc = frappe.get_doc(doc.get('doctype'), doc.get('amended_from'))
		return check_amended_from(amend_doc)
	return doc.get('name')


@frappe.whitelist()
def sync(data):
	data = json.loads(data)
	for row in data['sync_hub_document']:
		doc = frappe.get_doc(data['ref_doctype'], row['document'])
		# make_stream_update_log(doc, row['update_type'])
		enqueued_method = (
			"stream_sync.stream_sync.doctype.stream_update_log.stream_update_log.make_stream_update_log"
		)
		jobs = get_jobs()
		if not jobs or enqueued_method not in jobs[frappe.local.site]:
			frappe.enqueue(
				enqueued_method, doc=doc, update_type=row['update_type'] , queue="long", enqueue_after_commit=True
			)
	return "Success"

@frappe.whitelist()
def get_doctype_sync(doctype, txt, searchfield, start, page_len, filters):
	consumer_doctype = list(set(frappe.db.get_all("Stream Consumer Doctype", filters={"stream_type": "Manual"},pluck="ref_doctype")))
	
	query = """
		SELECT name AS value FROM `tabDocType`
		WHERE name IN %(name)s AND name LIKE %(txt)s
	"""
	cond = {
		'name': consumer_doctype,
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len
	}

	results = frappe.db.sql(query, cond)
	return results