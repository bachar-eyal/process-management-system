import re
import sqlite3


def extract_id(label: str) -> str | None:
	if not label:
		return None
	m = re.search(r"\((\d+)\)", label)
	return m.group(1) if m else None


def main():
	conn = sqlite3.connect('database.db')
	c = conn.cursor()

	# Ensure columns exist
	c.execute("PRAGMA table_info(process_tags)")
	cols = [col[1] for col in c.fetchall()]
	missing = []
	for col in ("performer", "checker", "performer_signature", "checker_signature"):
		if col not in cols:
			missing.append(col)
	if missing:
		print("Missing columns in process_tags:", ", ".join(missing))
		print("Please open the app once to run init_db and migrations, then retry.")
		return

	c.execute("SELECT tag_id, performer, checker FROM process_tags WHERE is_closed = 0")
	rows = c.fetchall()
	updated_perf = 0
	updated_check = 0

	for tag_id, performer, checker in rows:
		perf_id = extract_id(performer)
		check_id = extract_id(checker)

		perf_sig = None
		check_sig = None

		if perf_id:
			c.execute("SELECT signature FROM team_members WHERE id_number = ?", (perf_id,))
			row = c.fetchone()
			perf_sig = row[0] if row else None
		if check_id:
			c.execute("SELECT signature FROM team_members WHERE id_number = ?", (check_id,))
			row = c.fetchone()
			check_sig = row[0] if row else None

		# Apply updates
		if perf_sig is not None:
			c.execute(
				"UPDATE process_tags SET performer_signature = ?, date_updated = datetime('now') WHERE tag_id = ?",
				(perf_sig, tag_id),
			)
			updated_perf += c.rowcount if hasattr(c, 'rowcount') else 0
		if check_sig is not None:
			c.execute(
				"UPDATE process_tags SET checker_signature = ?, date_updated = datetime('now') WHERE tag_id = ?",
				(check_sig, tag_id),
			)
			updated_check += c.rowcount if hasattr(c, 'rowcount') else 0

	conn.commit()
	print(f"Updated open tags → performer_signature: {updated_perf}, checker_signature: {updated_check}")
	conn.close()


if __name__ == "__main__":
	main()
