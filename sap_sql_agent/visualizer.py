"""
SAP Open SQL Generator - ER Diyagrami Gorsellestirme.

HTML/CSS/SVG tabanli modern, okunabilir tablo iliski diyagrami.
Tablolar JOIN zinciri sirasina gore yatay olarak dizilir.
"""
import math
import re
from html import escape as html_escape


# =============================================
# TASARIM SABITLERI
# =============================================
CARD_WIDTH = 230
CARD_HEADER_H = 42
CARD_FIELD_H = 30
CARD_PADDING_BOTTOM = 6
CARD_GAP_X = 90       # kartlar arasi yatay bosluk (ok icin yer)
CONTAINER_PAD_X = 30   # sol/sag ic bosluk
CONTAINER_PAD_TOP = 24
CONTAINER_PAD_BOTTOM = 16

# Yay (arc) baglanti sabitleri
ARC_PER_SKIP = 35          # atlanan her ara tablo icin ek yay yuksekligi
PORT_STEP_Y = 22           # ayni kenardan cikan coklu oklar arasindaki Y ofseti

# Renk paleti
C = {
    "bg": "#0d1117",
    "wrapper_border": "#21262d",
    "card_bg": "#161b22",
    "card_border": "#30363d",
    "card_hover_border": "rgba(255,87,34,0.5)",
    "header_grad_start": "#FF5722",
    "header_grad_end": "#FF9800",
    "header_text": "#FFFFFF",
    "field_text": "#e6edf3",
    "field_text_dim": "#8b949e",
    "pk_color": "#3fb950",
    "pk_bg": "rgba(63,185,80,0.08)",
    "pk_border": "rgba(63,185,80,0.25)",
    "fk_color": "#58a6ff",
    "fk_bg": "rgba(88,166,255,0.08)",
    "fk_border": "rgba(88,166,255,0.25)",
    "highlight_color": "#f0883e",
    "highlight_bg": "rgba(240,136,62,0.10)",
    "highlight_border": "rgba(240,136,62,0.5)",
    "line_color": "#FF8A65",
    "line_label_bg": "#1c2128",
    "line_label_border": "#FF8A65",
    "badge_bg": "rgba(255,255,255,0.06)",
    "badge_text": "#8b949e",
    "row_hover": "rgba(255,255,255,0.03)",
    "row_alt": "rgba(255,255,255,0.015)",
}


def _card_height(n_fields: int) -> int:
    """Tablo kartinin piksel yuksekligini hesaplar."""
    return CARD_HEADER_H + n_fields * CARD_FIELD_H + CARD_PADDING_BOTTOM


def _order_by_join_chain(table_names: list, relationships: list) -> list:
    """
    Tablolari JOIN zinciri sirasina gore siralar.
    Ana tablo (master) ilk sirada, alt tablolar sirasyla sonra gelir.
    """
    if len(table_names) <= 1:
        return list(table_names)

    tset = set(table_names)

    # Yonsuz komsuluk grafi olustur
    adj = {t: [] for t in table_names}
    for rel in relationships:
        s, t = rel["source_table"], rel["target_table"]
        if s in tset and t in tset:
            if t not in adj[s]:
                adj[s].append(t)
            if s not in adj[t]:
                adj[t].append(s)

    # Kok tabloyu bul: 1:N iliskinin "1" tarafindaki tablo
    # (hicbir iliskide "N" tarafinda olmayan tablo)
    n_sides = set()
    for rel in relationships:
        s, t = rel["source_table"], rel["target_table"]
        if s in tset and t in tset:
            rtype = rel["relationship_type"]
            if rtype == "1:N":
                n_sides.add(t)
            elif rtype == "N:1":
                n_sides.add(s)

    root_candidates = [t for t in table_names if t not in n_sides]
    root = root_candidates[0] if root_candidates else table_names[0]

    # BFS ile zincir sirasi olustur
    ordered = [root]
    visited = {root}
    queue = [root]
    while queue:
        current = queue.pop(0)
        for neighbor in adj.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                ordered.append(neighbor)
                queue.append(neighbor)

    # Bagli olmayan tablolari sona ekle
    for t in table_names:
        if t not in visited:
            ordered.append(t)

    return ordered


def _compute_layout(table_names: list, card_heights: dict, arc_top_space: int = 0) -> tuple:
    """
    Tablo kartlari icin YATAY ZINCIR pozisyonlari hesaplar.
    Tum tablolar soldan saga dizilir (JOIN zinciri akisi).
    arc_top_space > 0 ise kartlarin ustunde yay oklar icin ek bosluk birakir.
    Returns: (positions_dict, total_content_height, container_width)
    """
    n = len(table_names)
    if n == 0:
        return {}, 100, 400

    # Tum tablolar tek satir - yatay chain layout
    container_w = CONTAINER_PAD_X * 2 + n * CARD_WIDTH + (n - 1) * CARD_GAP_X
    max_h = max(card_heights[t] for t in table_names)

    positions = {}
    for i, tname in enumerate(table_names):
        x = CONTAINER_PAD_X + i * (CARD_WIDTH + CARD_GAP_X)
        y = CONTAINER_PAD_TOP + arc_top_space
        positions[tname] = (x, y, card_heights[tname])

    content_h = CONTAINER_PAD_TOP + arc_top_space + max_h + CONTAINER_PAD_BOTTOM
    return positions, content_h, container_w


def _edge_connection(src_pos: tuple, tgt_pos: tuple) -> tuple:
    """
    Yatay zincirde: sag kenar -> sol kenar baglantisi.
    Returns: (x1, y1, x2, y2)
    """
    sx, sy, sh = src_pos
    tx, ty, th = tgt_pos

    src_cx = sx + CARD_WIDTH / 2
    tgt_cx = tx + CARD_WIDTH / 2

    # Hedef saga mi sola mi?
    if tgt_cx > src_cx:
        # saga gidiyor: kaynak sag kenar -> hedef sol kenar
        x1 = sx + CARD_WIDTH + 2
        x2 = tx - 2
    else:
        # sola gidiyor: kaynak sol kenar -> hedef sag kenar
        x1 = sx - 2
        x2 = tx + CARD_WIDTH + 2

    # Dikey ortada bagla (her kartin kendi yuksekliginin ortasi)
    y1 = sy + min(sh, 120) / 2 + 20
    y2 = ty + min(th, 120) / 2 + 20

    return x1, y1, x2, y2


def _bezier_path(x1, y1, x2, y2) -> str:
    """Smooth cubic bezier SVG path olusturur."""
    dx = x2 - x1
    mid = dx * 0.4
    return f"M {x1:.1f} {y1:.1f} C {x1 + mid:.1f} {y1:.1f}, {x2 - mid:.1f} {y2:.1f}, {x2:.1f} {y2:.1f}"


# =============================================
# CSS STIL TANIMLARI
# =============================================
_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

.er-wrapper {{
    background: {C['bg']};
    border-radius: 14px;
    border: 1px solid {C['wrapper_border']};
    overflow: auto;
    padding: 8px;
}}
.er-container {{
    position: relative;
}}
.er-svg {{
    position: absolute;
    top: 0; left: 0;
    pointer-events: none;
    z-index: 1;
}}

/* ===== TABLO KARTI ===== */
.er-card {{
    position: absolute;
    border-radius: 12px;
    border: 1px solid {C['card_border']};
    background: {C['card_bg']};
    box-shadow: 0 4px 20px rgba(0,0,0,0.35), 0 1px 3px rgba(0,0,0,0.2);
    overflow: hidden;
    z-index: 2;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}}
.er-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.45), 0 0 0 1px {C['card_hover_border']};
    border-color: {C['card_hover_border']};
}}

/* Kart Baslik */
.er-card-header {{
    background: linear-gradient(135deg, {C['header_grad_start']} 0%, {C['header_grad_end']} 100%);
    padding: 0 12px;
    display: flex;
    align-items: center;
    gap: 6px;
    height: {CARD_HEADER_H}px;
    box-sizing: border-box;
}}
.er-card-header .t-icon {{
    font-size: 16px;
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}}
.er-card-header .t-name {{
    color: {C['header_text']};
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.5px;
    text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.er-card-header .t-badge {{
    margin-left: auto;
    color: rgba(255,255,255,0.75);
    font-size: 9px;
    font-family: 'JetBrains Mono', Consolas, monospace;
    background: rgba(255,255,255,0.15);
    padding: 2px 6px;
    border-radius: 10px;
    white-space: nowrap;
    flex-shrink: 0;
}}

/* Kart Govde */
.er-card-body {{
    padding: 3px 0;
}}

/* ===== ALAN SATIRI ===== */
.f-row {{
    display: flex;
    align-items: center;
    padding: 0 10px;
    height: {CARD_FIELD_H}px;
    box-sizing: border-box;
    gap: 6px;
    transition: background 0.15s ease;
    cursor: default;
}}
.f-row:nth-child(even) {{
    background: {C['row_alt']};
}}
.f-row:hover {{
    background: {C['row_hover']};
}}

/* PK/FK satirlari */
.f-row.pk-row {{ background: {C['pk_bg']}; }}
.f-row.fk-row {{ background: {C['fk_bg']}; }}
.f-row.pk-row:hover {{ background: rgba(63,185,80,0.12); }}
.f-row.fk-row:hover {{ background: rgba(88,166,255,0.12); }}

/* Vurgulu satirlar */
.f-row.hl {{
    background: {C['highlight_bg']} !important;
    border-left: 3px solid {C['highlight_border']};
    padding-left: 7px;
}}
.f-row.hl:hover {{
    background: rgba(240,136,62,0.16) !important;
}}

/* Anahtar rozeti */
.f-key {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 26px;
    height: 17px;
    border-radius: 4px;
    font-size: 8px;
    font-weight: 700;
    font-family: 'JetBrains Mono', Consolas, monospace;
    flex-shrink: 0;
    letter-spacing: 0.5px;
}}
.f-key.pk {{
    background: {C['pk_bg']};
    color: {C['pk_color']};
    border: 1px solid {C['pk_border']};
}}
.f-key.fk {{
    background: {C['fk_bg']};
    color: {C['fk_color']};
    border: 1px solid {C['fk_border']};
}}
.f-key.none {{
    background: transparent;
    border: 1px solid transparent;
    color: transparent;
}}

/* Alan adi */
.f-name {{
    color: {C['field_text']};
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 11px;
    font-weight: 600;
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.f-row.hl .f-name {{
    color: {C['highlight_color']};
}}

/* Alan aciklamasi */
.f-desc {{
    color: {C['field_text_dim']};
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 65px;
    flex-shrink: 1;
}}

/* Veri tipi rozeti */
.f-type {{
    color: {C['badge_text']};
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 8px;
    background: {C['badge_bg']};
    padding: 2px 5px;
    border-radius: 4px;
    flex-shrink: 0;
}}

/* ===== LEJANT ===== */
.er-legend {{
    position: absolute;
    left: 0; right: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    padding: 12px 0 4px 0;
    z-index: 3;
    border-top: 1px solid {C['wrapper_border']};
}}
.leg-item {{
    display: flex;
    align-items: center;
    gap: 5px;
    color: {C['field_text_dim']};
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 9px;
    white-space: nowrap;
}}
.leg-dot {{
    width: 10px; height: 10px;
    border-radius: 3px;
    display: inline-block;
}}
.leg-dot.pk-d {{ background: {C['pk_color']}; opacity: 0.7; }}
.leg-dot.fk-d {{ background: {C['fk_color']}; opacity: 0.7; }}
.leg-dot.hl-d {{ background: {C['highlight_color']}; opacity: 0.7; }}
.leg-line {{
    width: 24px; height: 2px;
    background: {C['line_color']};
    border-radius: 1px;
    display: inline-block;
}}

/* ===== SIRA NUMARASI ===== */
.er-order {{
    position: absolute;
    top: -12px;
    left: -12px;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: linear-gradient(135deg, {C['header_grad_start']}, {C['header_grad_end']});
    color: white;
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 12px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(255,87,34,0.4);
    z-index: 5;
}}

/* ===== ANIMASYON ===== */
@keyframes fadeSlideIn {{
    from {{ opacity: 0; transform: translateX(-16px); }}
    to   {{ opacity: 1; transform: translateX(0); }}
}}
.er-card {{
    animation: fadeSlideIn 0.4s ease-out both;
}}
.er-card:nth-child(2) {{ animation-delay: 0.08s; }}
.er-card:nth-child(3) {{ animation-delay: 0.16s; }}
.er-card:nth-child(4) {{ animation-delay: 0.24s; }}
.er-card:nth-child(5) {{ animation-delay: 0.32s; }}
.er-card:nth-child(6) {{ animation-delay: 0.40s; }}
.er-card:nth-child(7) {{ animation-delay: 0.48s; }}
.er-card:nth-child(8) {{ animation-delay: 0.56s; }}

@keyframes drawLine {{
    from {{ stroke-dashoffset: 1000; }}
    to   {{ stroke-dashoffset: 0; }}
}}
.rel-path {{
    stroke-dasharray: 1000;
    animation: drawLine 0.8s ease-out 0.3s both;
}}
</style>
"""


# =============================================
# SVG TANIMLARI
# =============================================
_SVG_DEFS = f"""
<defs>
    <marker id="er-arrow" viewBox="0 0 12 8" refX="11" refY="4"
            markerWidth="10" markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 12 4 L 0 8 L 3 4 Z" fill="{C['line_color']}" opacity="0.85"/>
    </marker>
    <filter id="line-glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur"/>
        <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
        </feMerge>
    </filter>
</defs>
"""


def _extract_joins_from_sql(sql_text: str, known_tables: set) -> list:
    """
    SQL sorgusundaki INNER JOIN / LEFT JOIN ifadelerini parse ederek
    iliski listesi olusturur. Boylece metadata'da tanimlanmamis olsa bile
    SQL'deki her JOIN diyagramda ok olarak gosterilir.

    Returns:
        list of dicts: [{source_table, target_table, source_fields, target_fields, relationship_type}]
    """
    if not sql_text:
        return []

    joins = []
    upper_sql = sql_text.upper()
    upper_known = {t.upper(): t for t in known_tables}

    # FROM tablosunu bul
    from_match = re.search(r'FROM\s+(\w+)', upper_sql)
    from_table = from_match.group(1) if from_match else None

    # Her JOIN ifadesini parse et
    join_pattern = r'(?:INNER\s+JOIN|LEFT\s+(?:OUTER\s+)?JOIN)\s+(\w+)\s+ON\s+(.*?)(?=(?:INNER|LEFT)\s+(?:OUTER\s+)?JOIN|WHERE|INTO|FOR|$)'
    for match in re.finditer(join_pattern, upper_sql, re.DOTALL):
        join_table = match.group(1).strip()
        on_clause = match.group(2).strip()

        # ON kosullarini parse et: tablo1~alan1 = tablo2~alan2
        conditions = re.findall(r'(\w+)~(\w+)\s*=\s*(\w+)~(\w+)', on_clause)

        if conditions:
            # Ilk condition'dan source/target belirle
            src_fields = []
            tgt_fields = []
            src_table = None
            tgt_table = None

            for t1, f1, t2, f2 in conditions:
                # join_table olan tarafi hedef yap
                if t1.upper() == join_table.upper():
                    tgt_table = t1
                    tgt_fields.append(f1)
                    src_table = t2
                    src_fields.append(f2)
                else:
                    src_table = t1
                    src_fields.append(f1)
                    tgt_table = t2
                    tgt_fields.append(f2)

            if src_table and tgt_table:
                # Orijinal case'e cevir (metadata'daki isimlere esle)
                src_orig = upper_known.get(src_table.upper(), src_table)
                tgt_orig = upper_known.get(tgt_table.upper(), tgt_table)

                joins.append({
                    "source_table": src_orig,
                    "target_table": tgt_orig,
                    "source_fields": src_fields,
                    "target_fields": tgt_fields,
                    "relationship_type": "JOIN",
                })

    return joins


def create_er_diagram_html(
    tables: dict,
    relationships: list,
    used_tables: list,
    highlighted_fields: list = None,
    sql_text: str = None,
) -> tuple:
    """
    Modern HTML/CSS/SVG ER diyagrami olusturur.
    Tablolar JOIN zinciri sirasina gore yatay dizilir.
    SQL'deki JOIN'ler parse edilerek tum iliskiler diyagramda gosterilir.

    Returns:
        (html_string, height_in_pixels) tuple
    """
    if not used_tables:
        return _empty_html("Kullanilan tablo bulunamadi"), 100

    hl_upper = {f.upper() for f in (highlighted_fields or [])}

    # Filtrele
    ftables = {k: v for k, v in tables.items() if k in used_tables}

    if not ftables:
        return _empty_html("Kullanilan tablo bulunamadi"), 100

    # Metadata iliskilerini filtrele
    meta_rels = [
        r for r in relationships
        if r["source_table"] in used_tables and r["target_table"] in used_tables
    ]

    # SQL'den JOIN iliskilerini cikar
    sql_joins = _extract_joins_from_sql(sql_text, set(ftables.keys())) if sql_text else []

    # Birlestir: SQL JOIN'leri oncelikli, metadata tamamlayici
    # Ayni tablo cifti icin tekrar ekleme
    seen_pairs = set()
    frels = []

    # Once SQL JOIN'leri (gercek sorgu akisini yansitir)
    for rel in sql_joins:
        pair = (rel["source_table"], rel["target_table"])
        pair_rev = (rel["target_table"], rel["source_table"])
        if pair not in seen_pairs and pair_rev not in seen_pairs:
            seen_pairs.add(pair)
            frels.append(rel)

    # Sonra metadata iliskileri (SQL'de olmayanlari tamamla)
    for rel in meta_rels:
        pair = (rel["source_table"], rel["target_table"])
        pair_rev = (rel["target_table"], rel["source_table"])
        if pair not in seen_pairs and pair_rev not in seen_pairs:
            seen_pairs.add(pair)
            frels.append(rel)

    # JOIN zinciri sirasina gore sirala (alfabetik degil!)
    table_names = _order_by_join_chain(list(ftables.keys()), frels)
    n = len(table_names)
    table_idx = {tname: i for i, tname in enumerate(table_names)}

    # Komsuluk analizi: herhangi bir iliski komsusuz (arc gerektiren) mu?
    max_skip = 0
    for r in frels:
        s, t = r["source_table"], r["target_table"]
        if s in table_idx and t in table_idx:
            gap = abs(table_idx[s] - table_idx[t])
            if gap > 1:
                max_skip = max(max_skip, gap - 1)

    # Arc icin gereken ust bosluk (dinamik)
    arc_top_space = (50 + max_skip * ARC_PER_SKIP) if max_skip > 0 else 0

    # Yukseklik ve pozisyon hesapla
    card_heights = {t: _card_height(len(ftables[t]["fields"])) for t in table_names}
    positions, content_h, cw = _compute_layout(table_names, card_heights, arc_top_space=arc_top_space)

    legend_h = 48
    total_h = content_h + legend_h

    # ── SVG ILISKILERI ────────────────────────────
    # Port ofset sayaci: ayni kenardan birden fazla ok ciktiginda Y kaydirmasi
    port_counters = {}   # key: (tablo_adi, kenar "R"/"L") -> siradaki ofset
    svg_parts = []

    for rel in frels:
        src = rel["source_table"]
        tgt = rel["target_table"]
        if src not in positions or tgt not in positions:
            continue

        si = table_idx[src]
        ti = table_idx[tgt]
        gap = abs(si - ti)
        is_arc = gap > 1

        sx, sy, sh = positions[src]
        tx, ty, th = positions[tgt]
        goes_right = ti > si

        # Baglanti noktalarinin X pozisyonlari
        if goes_right:
            x1 = sx + CARD_WIDTH + 2
            x2 = tx - 2
            side_src, side_tgt = "R", "L"
        else:
            x1 = sx - 2
            x2 = tx + CARD_WIDTH + 2
            side_src, side_tgt = "L", "R"

        # Port ofsetleri (ayni kenardan cikan coklu oklar icin Y kaydirmasi)
        key_src = (src, side_src)
        key_tgt = (tgt, side_tgt)
        off_src = port_counters.get(key_src, 0)
        off_tgt = port_counters.get(key_tgt, 0)
        port_counters[key_src] = off_src + 1
        port_counters[key_tgt] = off_tgt + 1

        y1 = sy + CARD_HEADER_H + 15 + off_src * PORT_STEP_Y
        y2 = ty + CARD_HEADER_H + 15 + off_tgt * PORT_STEP_Y

        if is_arc:
            # Komsusuz baglanti: yay (arc) ile kartlarin USTUNDEN gec
            skip = gap - 1
            peak_y = sy - 15 - skip * ARC_PER_SKIP
            ctrl_dx = min(40, abs(x2 - x1) * 0.12)
            path_d = (
                f"M {x1:.1f} {y1:.1f} "
                f"C {x1 + ctrl_dx:.1f} {peak_y:.1f}, "
                f"{x2 - ctrl_dx:.1f} {peak_y:.1f}, "
                f"{x2:.1f} {y2:.1f}"
            )
            mx = (x1 + x2) / 2
            # Etiket: bezier egrisi yaklasik olarak peak_y+12 civarina gelir
            my = peak_y + 10
        else:
            # Komsu baglanti: dogrudan yatay bezier
            path_d = _bezier_path(x1, y1, x2, y2)
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2

        src_f = "+".join(rel["source_fields"])
        tgt_f = "+".join(rel["target_fields"])
        join_label = f"{src_f} = {tgt_f}"
        rel_type = rel["relationship_type"]

        lbl_w = max(len(join_label), len(rel_type) + 2) * 6.5 + 20
        lbl_h = 36

        svg_parts.append(f'''
            <path class="rel-path" d="{path_d}" fill="none"
                  stroke="{C['line_color']}" stroke-width="2" opacity="0.7"
                  marker-end="url(#er-arrow)" filter="url(#line-glow)"/>
            <rect x="{mx - lbl_w/2:.1f}" y="{my - lbl_h/2:.1f}"
                  width="{lbl_w:.0f}" height="{lbl_h}" rx="8"
                  fill="{C['line_label_bg']}" stroke="{C['line_label_border']}"
                  stroke-width="1" opacity="0.95"/>
            <text x="{mx:.1f}" y="{my - 3:.1f}" text-anchor="middle"
                  fill="{C['line_color']}" font-size="10"
                  font-family="'JetBrains Mono',Consolas,monospace"
                  font-weight="500">{html_escape(join_label)}</text>
            <text x="{mx:.1f}" y="{my + 10:.1f}" text-anchor="middle"
                  fill="#FFB74D" font-size="9" font-weight="700"
                  font-family="'JetBrains Mono',Consolas,monospace">{html_escape(rel_type)}</text>
        ''')

    svg_block = f'''
        <svg class="er-svg" width="{cw}" height="{total_h:.0f}"
             viewBox="0 0 {cw} {total_h:.0f}">
            {_SVG_DEFS}
            {"".join(svg_parts)}
        </svg>
    '''

    # ── TABLO KARTLARI ────────────────────────────
    cards_html = []
    for idx, tname in enumerate(table_names):
        x, y, h = positions[tname]
        fields = ftables[tname]["fields"]
        is_custom = tname.upper().startswith("Z")
        icon = "⚙️" if is_custom else "📋"

        # Alan satirlari
        rows = []
        for fi, f in enumerate(fields):
            fname = f["name"]
            ftype = f["data_type"]
            fdesc = f.get("description", "")
            fkey = f["key"]

            cls_parts = ["f-row"]
            if fkey == "PK":
                cls_parts.append("pk-row")
                key_html = '<span class="f-key pk">PK</span>'
            elif fkey == "FK":
                cls_parts.append("fk-row")
                key_html = '<span class="f-key fk">FK</span>'
            else:
                key_html = '<span class="f-key none">&middot;</span>'

            if fname.upper() in hl_upper:
                cls_parts.append("hl")

            desc_html = ""
            if fdesc:
                desc_html = f'<span class="f-desc" title="{html_escape(fdesc)}">{html_escape(fdesc)}</span>'

            rows.append(f'''
                <div class="{' '.join(cls_parts)}" title="{html_escape(fdesc)}">
                    {key_html}
                    <span class="f-name">{html_escape(fname)}</span>
                    {desc_html}
                    <span class="f-type">{html_escape(ftype)}</span>
                </div>
            ''')

        badge_text = f"{len(fields)} alan"

        cards_html.append(f'''
            <div class="er-card" style="left:{x:.0f}px; top:{y:.0f}px; width:{CARD_WIDTH}px;">
                <div class="er-order">{idx + 1}</div>
                <div class="er-card-header">
                    <span class="t-icon">{icon}</span>
                    <span class="t-name">{html_escape(tname)}</span>
                    <span class="t-badge">{badge_text}</span>
                </div>
                <div class="er-card-body">
                    {"".join(rows)}
                </div>
            </div>
        ''')

    # ── LEJANT ────────────────────────────
    legend_html = f'''
        <div class="er-legend" style="top:{content_h:.0f}px; width:{cw}px;">
            <span class="leg-item"><span class="leg-dot pk-d"></span> Primary Key</span>
            <span class="leg-item"><span class="leg-dot fk-d"></span> Foreign Key</span>
            <span class="leg-item"><span class="leg-dot hl-d"></span> Sorguda Kullanilan</span>
            <span class="leg-item"><span class="leg-line"></span> Iliski / JOIN</span>
        </div>
    '''

    # ── BIRLESIK HTML ────────────────────────────
    auto_scale_script = """
    <script>
    (function() {
        var wrapper = document.querySelector('.er-wrapper');
        var container = document.querySelector('.er-container');
        if (!wrapper || !container) return;
        var contentW = parseInt(container.style.width);
        var contentH = parseInt(container.style.height);
        function rescale() {
            var availW = document.documentElement.clientWidth - 24;
            if (contentW > availW && contentW > 0) {
                var s = availW / contentW;
                container.style.transform = 'scale(' + s + ')';
                container.style.transformOrigin = 'top left';
                wrapper.style.height = Math.ceil(contentH * s) + 'px';
                wrapper.style.overflow = 'hidden';
            } else {
                container.style.transform = '';
                wrapper.style.height = '';
                wrapper.style.overflow = 'auto';
            }
        }
        rescale();
        window.addEventListener('resize', rescale);
    })();
    </script>
    """

    full_html = f"""
    {_CSS}
    <div class="er-wrapper">
        <div class="er-container" style="width:{cw}px; height:{total_h:.0f}px;">
            {svg_block}
            {"".join(cards_html)}
            {legend_html}
        </div>
    </div>
    {auto_scale_script}
    """

    return full_html, int(total_h) + 30


def _empty_html(message: str) -> str:
    """Bos durum icin bilgilendirme HTML'i."""
    return f"""
    <div style="text-align:center; padding:48px 24px; color:#8b949e;
                font-family:'JetBrains Mono',Consolas,monospace; font-size:14px;
                background:#161b22; border-radius:14px; border:1px solid #30363d;">
        <div style="font-size:32px; margin-bottom:12px;">📊</div>
        {html_escape(message)}
    </div>
    """


# =============================================
# SQL PARSER
# =============================================
def extract_fields_from_sql(sql_text: str) -> list:
    """SQL metninden kullanilan alan adlarini cikarir."""
    if not sql_text:
        return []

    fields = set()
    upper_sql = sql_text.upper()

    # SELECT ile FROM arasindaki alanlari parse et
    select_match = re.search(r"SELECT\s+(.*?)\s+FROM\s+", upper_sql, re.DOTALL)
    if select_match:
        select_part = select_match.group(1)
        for token in re.split(r"[\s,]+", select_part):
            token = token.strip()
            if "~" in token:
                fields.add(token.split("~")[1])
            elif token and token not in ("DISTINCT", "SINGLE", "UP", "TO", "ROWS"):
                fields.add(token)

    # WHERE kosullarindaki alanlari bul
    where_match = re.search(r"WHERE\s+(.*?)(?:\.\s*$|$)", upper_sql, re.DOTALL)
    if where_match:
        where_part = where_match.group(1)
        for token in re.findall(
            r"(\w+~\w+|\b[A-Z_]+\b)\s*(?:=|<>|<|>|<=|>=|LIKE|BETWEEN|IN)", where_part
        ):
            if "~" in token:
                fields.add(token.split("~")[1])
            else:
                fields.add(token)

    # ON kosullarindaki JOIN alanlarini bul
    for on_match in re.finditer(r"ON\s+(.*?)(?:INNER|LEFT|WHERE|INTO|$)", upper_sql, re.DOTALL):
        on_part = on_match.group(1)
        for token in re.findall(r"(\w+~\w+)", on_part):
            fields.add(token.split("~")[1])

    # Anahtar kelimeleri cikar
    noise = {
        "AND", "OR", "NOT", "IN", "BETWEEN", "LIKE", "IS", "NULL", "INTO",
        "TABLE", "DATA", "CORRESPONDING", "FIELDS", "OF", "FOR", "ALL",
        "ENTRIES", "WHERE", "FROM", "SELECT", "INNER", "JOIN", "LEFT",
        "OUTER", "ON", "0", "",
    }
    fields -= noise

    return list(fields)
