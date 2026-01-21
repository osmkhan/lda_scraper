"""
SQLite database schema with FTS5 full-text search for LDA Transparency Database.
"""

import sqlite3
from pathlib import Path
from typing import Optional
import json


class LDADatabase:
    """Main database class for LDA transparency tracking."""

    def __init__(self, db_path: str = "lda_transparency.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def initialize(self):
        """Initialize database schema with all tables."""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        # Documents table - main table for all documents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                file_path TEXT,
                date_published DATE,
                date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                page_count INTEGER,
                file_size INTEGER,
                is_scanned BOOLEAN DEFAULT 0,
                extraction_method TEXT,
                source_page TEXT,
                metadata TEXT
            )
        """)

        # Document content table with extracted text
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                page_number INTEGER,
                content TEXT NOT NULL,
                language TEXT DEFAULT 'eng',
                ocr_confidence REAL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Tags table for advocacy topics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                description TEXT
            )
        """)

        # Document-tags junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_tags (
                document_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                confidence REAL DEFAULT 1.0,
                PRIMARY KEY (document_id, tag_id),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)

        # Meeting minutes specific table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meeting_minutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL UNIQUE,
                meeting_date DATE,
                meeting_type TEXT,
                attendees TEXT,
                agenda_items TEXT,
                decisions TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Regulations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL UNIQUE,
                regulation_type TEXT,
                effective_date DATE,
                supersedes INTEGER,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (supersedes) REFERENCES regulations(id)
            )
        """)

        # Housing schemes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS housing_schemes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL UNIQUE,
                scheme_name TEXT NOT NULL,
                location TEXT,
                developer TEXT,
                approval_status TEXT,
                approval_date DATE,
                total_area REAL,
                plot_count INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Tenders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL UNIQUE,
                tender_number TEXT,
                tender_title TEXT,
                tender_type TEXT,
                issue_date DATE,
                closing_date DATE,
                opening_date DATE,
                estimated_cost REAL,
                status TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title,
                content,
                document_type,
                tags,
                content=document_content,
                content_rowid=id,
                tokenize='porter unicode61'
            )
        """)

        # Triggers to keep FTS table in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_insert AFTER INSERT ON document_content
            BEGIN
                INSERT INTO documents_fts(rowid, title, content, document_type, tags)
                SELECT
                    NEW.id,
                    d.title,
                    NEW.content,
                    d.document_type,
                    COALESCE(
                        (SELECT GROUP_CONCAT(t.name, ' ')
                         FROM document_tags dt
                         JOIN tags t ON dt.tag_id = t.id
                         WHERE dt.document_id = d.id),
                        ''
                    )
                FROM documents d
                WHERE d.id = NEW.document_id;
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_update AFTER UPDATE ON document_content
            BEGIN
                UPDATE documents_fts
                SET content = NEW.content
                WHERE rowid = NEW.id;
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_delete AFTER DELETE ON document_content
            BEGIN
                DELETE FROM documents_fts WHERE rowid = OLD.id;
            END
        """)

        # Indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_type
            ON documents(document_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_date
            ON documents(date_published)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_content_doc_id
            ON document_content(document_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_tags_doc_id
            ON document_tags(document_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_tags_tag_id
            ON document_tags(tag_id)
        """)

        self.conn.commit()
        print("Database schema initialized successfully.")

    def insert_document(self, document_type: str, title: str, url: str, **kwargs) -> Optional[int]:
        """Insert a new document and return its ID."""
        cursor = self.conn.cursor()

        # Build the INSERT statement dynamically
        fields = ['document_type', 'title', 'url']
        values = [document_type, title, url]

        for key, value in kwargs.items():
            if value is not None:
                fields.append(key)
                values.append(value)

        placeholders = ', '.join(['?' for _ in values])
        fields_str = ', '.join(fields)

        try:
            cursor.execute(
                f"INSERT INTO documents ({fields_str}) VALUES ({placeholders})",
                values
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Document already exists
            cursor.execute("SELECT id FROM documents WHERE url = ?", (url,))
            result = cursor.fetchone()
            return result[0] if result else None

    def insert_content(self, document_id: int, content: str, page_number: Optional[int] = None, **kwargs):
        """Insert document content."""
        cursor = self.conn.cursor()

        fields = ['document_id', 'content']
        values = [document_id, content]

        if page_number is not None:
            fields.append('page_number')
            values.append(page_number)

        for key, value in kwargs.items():
            if value is not None:
                fields.append(key)
                values.append(value)

        placeholders = ', '.join(['?' for _ in values])
        fields_str = ', '.join(fields)

        cursor.execute(
            f"INSERT INTO document_content ({fields_str}) VALUES ({placeholders})",
            values
        )
        self.conn.commit()

    def insert_tag(self, name: str, category: str, description: Optional[str] = None) -> int:
        """Insert a tag and return its ID."""
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO tags (name, category, description) VALUES (?, ?, ?)",
                (name, category, description)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Tag already exists
            cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
            result = cursor.fetchone()
            return result[0]

    def tag_document(self, document_id: int, tag_id: int, confidence: float = 1.0):
        """Associate a tag with a document."""
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO document_tags (document_id, tag_id, confidence) VALUES (?, ?, ?)",
                (document_id, tag_id, confidence)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            # Association already exists
            pass

    def search_documents(self, query: str, limit: int = 50):
        """Full-text search across all documents."""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                d.id,
                d.document_type,
                d.title,
                d.url,
                d.date_published,
                snippet(documents_fts, 1, '<mark>', '</mark>', '...', 50) as snippet,
                rank
            FROM documents_fts
            JOIN documents d ON documents_fts.rowid = d.id
            WHERE documents_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))

        return cursor.fetchall()

    def get_document_stats(self):
        """Get statistics about the database."""
        cursor = self.conn.cursor()

        stats = {}

        # Total documents
        cursor.execute("SELECT COUNT(*) FROM documents")
        stats['total_documents'] = cursor.fetchone()[0]

        # Documents by type
        cursor.execute("""
            SELECT document_type, COUNT(*)
            FROM documents
            GROUP BY document_type
        """)
        stats['by_type'] = dict(cursor.fetchall())

        # Total tags
        cursor.execute("SELECT COUNT(*) FROM tags")
        stats['total_tags'] = cursor.fetchone()[0]

        # Most common tags
        cursor.execute("""
            SELECT t.name, t.category, COUNT(*) as count
            FROM document_tags dt
            JOIN tags t ON dt.tag_id = t.id
            GROUP BY t.id
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['top_tags'] = cursor.fetchall()

        return stats


def create_database(db_path: str = "lda_transparency.db"):
    """Create and initialize the database."""
    db = LDADatabase(db_path)
    db.connect()
    db.initialize()
    db.close()
    return db_path


if __name__ == "__main__":
    # Create the database
    db_path = create_database()
    print(f"Database created at: {db_path}")
