"""
SAP Open SQL Generator - Excel Metadata Parser ve Tablo Filtreleme.

Excel dosyasindan SAP tablo metadata'sini okur, yapilandirir
ve LLM prompt'ina uygun formata cevirir.
"""
import pandas as pd


def load_metadata_from_excel(uploaded_file):
    """
    Excel dosyasini parse ederek tablo ve iliski metadata'si olusturur.

    Args:
        uploaded_file: Streamlit file_uploader'dan gelen dosya

    Returns:
        (tables_dict, relationships_list, error_message_or_None)
    """
    try:
        # Sheet 1: Tablolar
        df_tables = pd.read_excel(
            uploaded_file, sheet_name="Tablolar", engine="openpyxl"
        )
        required_cols_tables = {"TABLO_ADI", "ALAN_ADI", "ALAN_ACIKLAMASI", "VERI_TIPI", "ANAHTAR"}
        missing = required_cols_tables - set(df_tables.columns)
        if missing:
            return None, None, f"Tablolar sayfasinda eksik sutunlar: {', '.join(missing)}"

        # Sheet 2: Iliskiler
        df_rels = pd.read_excel(
            uploaded_file, sheet_name="Iliskiler", engine="openpyxl"
        )
        required_cols_rels = {"KAYNAK_TABLO", "KAYNAK_ALAN", "HEDEF_TABLO", "HEDEF_ALAN", "ILISKI_TIPI"}
        missing_rels = required_cols_rels - set(df_rels.columns)
        if missing_rels:
            return None, None, f"Iliskiler sayfasinda eksik sutunlar: {', '.join(missing_rels)}"

        # Tablolari dict'e cevir
        tables = {}
        for _, row in df_tables.iterrows():
            table_name = str(row["TABLO_ADI"]).strip().upper()
            if table_name not in tables:
                tables[table_name] = {"fields": []}

            key_val = str(row.get("ANAHTAR", "")).strip().upper()
            if key_val in ("NAN", "NONE", ""):
                key_val = ""

            tables[table_name]["fields"].append({
                "name": str(row["ALAN_ADI"]).strip().upper(),
                "description": str(row["ALAN_ACIKLAMASI"]).strip(),
                "data_type": str(row["VERI_TIPI"]).strip().upper(),
                "key": key_val,
            })

        # Iliskileri list'e cevir
        relationships = []
        for _, row in df_rels.iterrows():
            source_fields_raw = str(row["KAYNAK_ALAN"]).strip().upper()
            target_fields_raw = str(row["HEDEF_ALAN"]).strip().upper()

            source_fields = [f.strip() for f in source_fields_raw.split("+")]
            target_fields = [f.strip() for f in target_fields_raw.split("+")]

            relationships.append({
                "source_table": str(row["KAYNAK_TABLO"]).strip().upper(),
                "source_fields": source_fields,
                "target_table": str(row["HEDEF_TABLO"]).strip().upper(),
                "target_fields": target_fields,
                "relationship_type": str(row["ILISKI_TIPI"]).strip(),
            })

        return tables, relationships, None

    except Exception as e:
        return None, None, f"Excel okuma hatasi: {str(e)}"


def get_table_summary(tables: dict) -> str:
    """Sidebar icin tablo ozeti HTML'i olusturur."""
    html_parts = []
    for table_name, table_data in sorted(tables.items()):
        fields = table_data["fields"]
        pk_fields = [f["name"] for f in fields if f["key"] == "PK"]
        pk_text = ", ".join(pk_fields) if pk_fields else "-"
        html_parts.append(
            f'<div class="metadata-card">'
            f'<span class="table-name">{table_name}</span> '
            f'<span class="field-count">({len(fields)} alan)</span><br>'
            f'<small>PK: {pk_text}</small>'
            f'</div>'
        )
    return "\n".join(html_parts)


def _build_relationship_graph(relationships: list) -> dict:
    """Iliskilerden komsusluk grafi olusturur."""
    graph = {}
    for rel in relationships:
        src = rel["source_table"]
        tgt = rel["target_table"]
        graph.setdefault(src, set()).add(tgt)
        graph.setdefault(tgt, set()).add(src)
    return graph


def _expand_tables_via_relationships(matched_tables: set, graph: dict, max_hops: int = 2) -> set:
    """Eslesen tablolardan max_hops mesafedeki tablolari da ekler."""
    expanded = set(matched_tables)
    frontier = set(matched_tables)
    for _ in range(max_hops):
        next_frontier = set()
        for table in frontier:
            for neighbor in graph.get(table, set()):
                if neighbor not in expanded:
                    expanded.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier
    return expanded


def _fuzzy_match(word1: str, word2: str, min_prefix: int = 3) -> bool:
    """
    Iki kelime arasinda fuzzy eslestirme yapar.
    Turkce ekler icin: birinin digeriyle baslayip baslamadigini kontrol eder.
    Ornek: 'deposunu' ve 'depo' -> True (depo, deposunu'nun prefix'i)
           'rengi' ve 'renk' -> True (renk, rengi'nin prefix'i)
    """
    if len(word1) < min_prefix or len(word2) < min_prefix:
        return False
    shorter = word1 if len(word1) <= len(word2) else word2
    longer = word1 if len(word1) > len(word2) else word2
    # Kisa kelime, uzun kelimenin basinda mi?
    return longer.startswith(shorter) and len(shorter) >= min_prefix


def find_relevant_tables(tables: dict, relationships: list, query: str):
    """
    Kullanici sorusundaki anahtar kelimelere gore ilgili tablolari filtreler.

    Skor bazli eslestirme yapar: PK olmayan (ayirt edici) alanlara
    daha yuksek puan verir. Sonra iliski grafi uzerinde komsu
    tablolari da dahil eder.

    Args:
        tables: Tum tablo metadata'si
        relationships: Tum iliskiler
        query: Kullanicinin Turkce sorusu

    Returns:
        (filtered_tables_dict, filtered_relationships_list)
    """
    query_lower = query.lower()
    # Turkce stop words'leri cikar
    stop_words = {
        "bir", "bu", "su", "o", "ve", "ile", "icin", "de", "da",
        "mi", "mu", "ne", "nasil", "hangi", "nedir", "nerede",
        "bana", "beni", "benim", "getir", "goster", "ver", "listele",
        "olan", "tum", "hepsi", "deki", "daki",
    }
    words = set(query_lower.split()) - stop_words
    # 2 harften kisa kelimeleri de cikar
    words = {w for w in words if len(w) > 2}

    if not words:
        return tables, relationships

    # Her tablo icin skor hesapla
    table_scores = {}
    for table_name, table_data in tables.items():
        score = 0
        table_name_lower = table_name.lower()

        # Tablo adinda eslesme (en yuksek skor)
        if any(_fuzzy_match(w, table_name_lower) for w in words):
            score += 10

        # Alan aciklamalarinda eslesme
        for field in table_data["fields"]:
            desc_words = field["description"].lower().split()
            field_name_lower = field["name"].lower()
            for w in words:
                matched = any(_fuzzy_match(w, dw) for dw in desc_words)
                if not matched:
                    matched = _fuzzy_match(w, field_name_lower)
                if matched:
                    # PK olmayan alanlara daha yuksek skor (ayirt edici)
                    if field["key"] != "PK":
                        score += 3
                    else:
                        score += 1

        if score > 0:
            table_scores[table_name] = score

    if not table_scores:
        return tables, relationships

    # Sadece anlamli skoru olan tablolari al (en az 2 puan)
    primary_tables = {t for t, s in table_scores.items() if s >= 2}

    # Eger primary cok azsa, tum skorlulari al
    if len(primary_tables) < 1:
        primary_tables = set(table_scores.keys())

    # Iliski grafi ile sadece 1 hop komsu tablolari da ekle
    graph = _build_relationship_graph(relationships)
    expanded = _expand_tables_via_relationships(primary_tables, graph, max_hops=1)

    # Eger genisleme tum tablolari kapsiyorsa, sadece primary + 1 hop'u tut
    total = len(tables)
    if len(expanded) > total * 0.7:
        # Cok genis: sadece yuksek skorlu tablolari ve dogrudan iliskilerini al
        top_tables = {t for t, s in table_scores.items() if s >= 3}
        if len(top_tables) >= 1:
            expanded = _expand_tables_via_relationships(top_tables, graph, max_hops=1)

    # Filtrele
    filtered_tables = {k: v for k, v in tables.items() if k in expanded}
    filtered_rels = [
        r for r in relationships
        if r["source_table"] in expanded and r["target_table"] in expanded
    ]

    if len(filtered_tables) < 1:
        return tables, relationships

    return filtered_tables, filtered_rels


def format_metadata_for_prompt(tables: dict, relationships: list) -> str:
    """
    Tablo ve iliski metadata'sini LLM prompt'ina uygun string formatina cevirir.
    Token-efficient, yapilandirilmis text ciktisi.
    """
    lines = ["=== TABLOLAR ===\n"]

    for table_name in sorted(tables.keys()):
        table_data = tables[table_name]
        lines.append(f"TABLO: {table_name}")
        lines.append("Alanlar:")
        for field in table_data["fields"]:
            key_str = f", {field['key']}" if field["key"] else ""
            lines.append(
                f"  - {field['name']} ({field['data_type']}{key_str}): {field['description']}"
            )
        lines.append("")

    lines.append("=== ILISKILER ===\n")
    for rel in relationships:
        src_fields = "+".join(rel["source_fields"])
        tgt_fields = "+".join(rel["target_fields"])
        lines.append(
            f"{rel['source_table']}.{src_fields} -> "
            f"{rel['target_table']}.{tgt_fields} ({rel['relationship_type']})"
        )

    return "\n".join(lines)
