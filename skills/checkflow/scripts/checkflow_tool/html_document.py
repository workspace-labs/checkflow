"""Draw the shared project document as a single offline HTML file."""

from base64 import b64encode
from html import escape

from .arabic import display, ltr_tokens
from .document_language import load
from .document_theme import for_language


STYLE = """
*{box-sizing:border-box}
html{background:var(--tint);color:var(--ink);font-family:var(--body)}
body{margin:0}
main{width:min(100%,66rem);margin-inline:auto;padding:clamp(1rem,4vw,3.5rem);
     background:white;overflow-wrap:anywhere}
h1,h2,h3,p,ol,ul,dl,dd{margin:0}
h1,h2{font-family:var(--heading)}
h2{font-size:clamp(1.2rem,2.6vw,1.56rem);line-height:1.25;color:var(--main)}
h3{font-size:.78rem;line-height:1.4;letter-spacing:.07em;text-transform:uppercase}
p,li,dd{line-height:1.55}
a{color:var(--main);text-underline-offset:.16em}
a:focus-visible{outline:2px solid var(--main);outline-offset:3px}
.official{font-size:.78rem;color:var(--quiet);padding-block-end:1rem}
.cover{border:1px solid var(--main);border-radius:var(--radius);
       padding:clamp(1rem,4vw,3.25rem);padding-block-start:clamp(1.5rem,5vw,4rem)}
.cover.register{outline:1px solid var(--line);outline-offset:-5px}
.cover.band{padding-block-start:0}
.cover.side{border-inline-start:clamp(8px,4vw,4rem) solid var(--main)}
.cover-heading.center{text-align:center}
.cover-heading h1{font-size:clamp(2.1rem,6vw,3.85rem);color:var(--main);line-height:1.1}
.cover-heading .doc-title{font-size:clamp(1rem,2.3vw,1.3rem);font-weight:bold;
                         margin-block:.5rem}
.cover-heading.center .doc-title::before{content:"";display:block;
    margin:.9rem auto .65rem;width:2.75rem;border-top:2px solid currentColor}
.cover-heading p:not(.doc-title){color:var(--quiet);font-size:.9rem}
.band .cover-heading{margin-inline:calc(-1 * clamp(1rem,4vw,3.25rem));
    background:var(--main);color:var(--on-main);padding:clamp(1.25rem,4vw,3rem);
    border-radius:var(--radius) var(--radius) 0 0}
.band .cover-heading h1,.band .cover-heading p:not(.doc-title){color:var(--on-main)}
.metrics,.details{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,8.5rem),1fr));
    margin-block:1.5rem 1.25rem;border-block:1px solid var(--line)}
.metrics div,.details div{min-width:0;padding:var(--space)}
.metrics div + div,.details.row div + div{border-inline-start:1px solid var(--line)}
.metrics dt{font-size:1.45rem;color:var(--main);font-weight:bold;font-variant-numeric:tabular-nums}
.metrics dd,.details{font-size:.78rem}
.details dt{color:var(--quiet);font-size:.7rem;text-transform:uppercase;letter-spacing:.05em}
.details dd{font-weight:bold}
.details.list{display:block}
.details.list div + div{border-block-start:1px solid var(--line)}
.details.list div{display:grid;grid-template-columns:minmax(7rem,1fr) 2fr;gap:var(--space)}
.contents{margin-block:1.45rem}
.contents h2,.cover-block h3{display:flex;align-items:center;gap:.75rem;color:var(--main);
                              font-family:var(--body);font-size:.78rem;letter-spacing:.06em;
                              text-transform:uppercase}
.contents h2::after,.cover-block h3::after{content:"";height:1px;min-width:1rem;
                                           background:var(--line);flex:1}
.contents ol{display:grid;grid-auto-flow:column;grid-template-rows:repeat(var(--contents-rows,5),auto);
             grid-template-columns:1fr 1fr;column-gap:1.3rem;
             list-style:none;padding:0;margin-block-start:.5rem}
.contents a{display:flex;align-items:baseline;gap:.65rem;min-height:2rem;
            padding-block:.2rem;border-block-end:1px dotted var(--line);
            font-size:.86rem;text-decoration:none}
.contents a:hover{text-decoration:underline}
.contents .page{margin-inline-start:auto;white-space:nowrap;color:var(--quiet);font-size:.75rem}
.cover-blocks{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem}
.cover-block:first-child{grid-column:1/-1}
.cover-block h3{margin-block-end:.65rem}
.cover-block p,.cover-block li{font-size:.87rem}
section{padding-block-start:1.9rem;scroll-margin-block-start:1rem}
section h2{margin-block-end:.95rem;padding-block-end:.45rem;border-block-end:1px solid var(--line)}
section h3{margin-block:1rem .35rem;color:var(--main)}
section p + p{margin-block-start:.5rem}
ul{padding-inline-start:1.12rem}
li::marker{color:var(--main)}
.timeline{display:flex;flex-wrap:wrap;gap:.75rem;list-style:none;
          padding:0;margin-block:.75rem .95rem}
.timeline li{flex:1;min-width:min(100%,7.75rem);padding-block-start:.45rem;
             border-block-start:2px solid var(--main);font-size:.82rem;color:var(--quiet)}
.timeline time{display:block;font-variant-numeric:tabular-nums;font-weight:bold;color:var(--ink)}
.callout{border-inline-start:3px solid var(--main);border-radius:var(--radius);
         padding:var(--space);background:var(--tint);margin-block:.75rem}
.signoff{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-block:.85rem 0}
.signoff > div{border:1px solid var(--line);border-block-start:2px solid var(--main);
               border-radius:var(--radius);padding:calc(var(--space) * 2);
               display:grid;grid-template-rows:auto 1fr auto}
.signoff dt{font-size:.76rem;color:var(--quiet);text-transform:uppercase;font-weight:bold}
.signoff .party{min-block-size:2.25rem;color:var(--main);font-size:.9rem;font-weight:bold}
.signature-lines{list-style:none;padding:0;font-size:.72rem;font-weight:bold;color:var(--quiet)}
.signature-lines li{min-block-size:2.25rem;margin-block-end:.35rem;
                    border-block-end:1px solid var(--line)}
table{width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;
      margin-block:.6rem .95rem;border-block-end:2px solid var(--main);font-size:.87rem}
th,td{text-align:start;vertical-align:top;padding:var(--space);line-height:1.4}
th{background:var(--main);color:var(--on-main);text-transform:uppercase;
   font-size:.68rem;letter-spacing:.06em}
th:first-child{border-start-start-radius:var(--radius)}
th:last-child{border-start-end-radius:var(--radius)}
td{border-block-end:1px solid var(--line);border-inline-end:1px solid var(--line)}
td:first-child{border-inline-start:1px solid var(--line)}
tbody tr:last-child td{border-block-end:0}
tbody tr:nth-child(even){background:var(--tint)}
.numeric{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;max-width:100%;padding:.18rem .35rem;background:#E0EEE4;
       color:#245338;border-radius:var(--radius);font-size:.72rem;font-weight:bold;
       text-transform:uppercase;line-height:1.3}
.badge.decision{background:#F8EDD1;color:#674500}
footer{margin-block-start:2rem;padding-block-start:.75rem;border-block-start:1px solid var(--line);
       color:var(--quiet);font-size:.78rem}
footer div{display:flex;gap:1rem;justify-content:space-between}
.credit{text-align:center;margin-block-start:1rem}
html[dir="rtl"] :is(h3,.details dt,.contents h2,.signoff dt,th,.badge){
    letter-spacing:normal;text-transform:none
}
@media screen and (max-width:640px){
 .contents ol{display:block}
 .contents a{min-height:2.3rem;align-items:center}
 .metrics{grid-template-columns:1fr 1fr}
 .metrics div{border-block-end:1px solid var(--line)}
 .metrics div:nth-child(2n + 1){border-inline-start:0}
 .metrics div:nth-last-child(2):nth-child(2n + 1),.metrics div:last-child{border-block-end:0}
 .details.row{display:block}
 .details.row div + div{border-inline-start:0;border-block-start:1px solid var(--line)}
 .cover-blocks{grid-template-columns:1fr}
 table.wide-table{display:block;border-block-start:4px solid var(--main)}
 .wide-table colgroup{display:none}
 .wide-table thead{position:absolute;width:1px;height:1px;overflow:hidden;
                   clip-path:inset(50%);white-space:nowrap}
 .wide-table tbody{display:block;width:100%}
 .wide-table tr{display:block;border-block-end:2px solid var(--line)}
 .wide-table tr:last-child{border-block-end:0}
 .wide-table td{display:grid;grid-template-columns:minmax(4.9rem,.42fr) minmax(0,1fr);
                align-items:start;gap:var(--space);border-inline-start:1px solid var(--line)}
 .wide-table td::before{content:attr(data-label);color:var(--quiet);font-weight:bold;
                        border-inline-end:1px solid var(--line);text-align:start;
                        padding-inline-end:var(--space)}
 .wide-table td > span{min-width:0}
 .wide-table .badge{justify-self:start}
 .wide-table tbody tr:last-child td:not(:last-child){border-block-end:1px solid var(--line)}
}
@media print{
 html{background:white}
 main{width:100%;padding:0}
 tr,.timeline li,.signoff{break-inside:avoid}
 thead{display:table-header-group}
 h2,h3{break-after:avoid}
}
"""


def font_css(face, name):
    if face.file is None:
        return "", "monospace"
    rules = []
    for weight, path, data in ((400, face.file, face.regular_data), (700, face.bold, face.bold_data)):
        if path is None:
            continue
        font = b64encode(data if data is not None else path.read_bytes()).decode("ascii")
        rules.append(
            f'@font-face{{font-family:{name};font-style:normal;font-weight:{weight};'
            f'src:url(data:font/ttf;base64,{font}) format("truetype")}}'
        )
    return "\n".join(rules), f"{name},sans-serif"


def styles(theme):
    body_rules, body = font_css(theme.body, "CheckflowBody")
    if theme.heading == theme.body:
        heading_rules, heading = "", body
    else:
        heading_rules, heading = font_css(theme.heading, "CheckflowHeading")
    return (
        f"{body_rules}\n{heading_rules}\n"
        f":root{{--main:{theme.main};--on-main:{theme.on_main};--ink:{theme.ink};"
        f"--quiet:{theme.quiet};--line:{theme.line};--tint:{theme.tint};"
        f"--radius:{theme.radius:g}px;--space:{theme.spacing:g}px;"
        f"--heading:{heading};--body:{body}}}\n{STYLE}"
    )


def numeric_class(block, column):
    return ' class="numeric"' if column in block.numeric else ""


def inline(value, rtl):
    if not rtl:
        return escape(value)
    value = display(value)
    moves = []
    start = 0
    for match in ltr_tokens(value):
        left, right = match.span()
        moves.extend((escape(value[start:left]), '<bdi dir="ltr">', escape(match[0]), "</bdi>"))
        start = right
    moves.append(escape(value[start:]))
    return "".join(moves)


def caps(value, rtl):
    return value if rtl else value.upper()


def cell(block, column, value, words, rtl):
    label = escape(display(block.headers[column]) if rtl else block.headers[column])
    if column in block.badges:
        decision = tuple(words[key].casefold() for key in ("Changed", "Changed, approved", "Keep"))
        status = " decision" if value.casefold().startswith(decision) else ""
        content = f'<span class="badge{status}">{inline(caps(value, rtl), rtl)}</span>'
    else:
        content = f"<span>{inline(value, rtl)}</span>"
    return f'<td role="cell"{numeric_class(block, column)} data-label="{label}">{content}</td>'


def table(block, words, rtl):
    wide = ' class="wide-table"' if len(block.headers) > 2 else ""
    columns = "".join(f'<col style="width:{width * 100:g}%">' for width in block.widths)
    headers = "".join(
        f'<th role="columnheader" scope="col"{numeric_class(block, index)}>'
        f'{inline(caps(label, rtl), rtl)}</th>' for index, label in enumerate(block.headers)
    )
    rows = "".join(
        '<tr role="row">' + "".join(cell(block, index, value, words, rtl)
                                    for index, value in enumerate(row)) + "</tr>"
        for row in block.rows
    )
    return (f'<table role="table"{wide}><colgroup>{columns}</colgroup>'
            f'<thead role="rowgroup"><tr role="row">{headers}</tr></thead>'
            f'<tbody role="rowgroup">{rows}</tbody></table>')


def block_html(block, words, rtl):
    if block.kind == "table":
        return table(block, words, rtl)
    if block.kind == "timeline":
        return '<ol class="timeline">' + "".join(
            f'<li><time datetime="{escape(date)}">{inline(date, rtl)}</time>{inline(label, rtl)}</li>'
            for date, label in block.rows
        ) + "</ol>"
    if block.kind == "signoff":
        lines = "".join(f"<li>{inline(field, rtl)}</li>" for field in block.headers)
        return '<dl class="signoff">' + "".join(
            f'<div><dt>{inline(label, rtl)}</dt><dd class="party">{inline(value, rtl)}</dd>'
            f'<dd><ul class="signature-lines">{lines}</ul></dd></div>'
            for label, value in block.rows
        ) + "</dl>"
    if block.kind == "subheading":
        return "".join(f"<h3>{inline(row[0], rtl)}</h3>" for row in block.rows)
    if block.kind == "list":
        return "<ul>" + "".join(f"<li>{inline(row[0], rtl)}</li>" for row in block.rows) + "</ul>"
    paragraphs = "".join(f"<p>{inline(row[0], rtl)}</p>" for row in block.rows)
    return f'<div class="callout">{paragraphs}</div>' if block.kind == "callout" else paragraphs


def description_list(pairs, css_class, rtl):
    if not pairs:
        return ""
    items = "".join(f"<div><dt>{inline(label, rtl)}</dt><dd>{inline(value, rtl)}</dd></div>"
                    for label, value in pairs)
    return f'<dl class="{escape(css_class)}">{items}</dl>'


def metrics(pairs, rtl):
    if not pairs:
        return ""
    return '<dl class="metrics">' + "".join(
        f"<div><dt>{inline(value, rtl)}</dt><dd>{inline(label, rtl)}</dd></div>"
        for value, label in pairs
    ) + "</dl>"


def section_title(section, words, rtl):
    return inline(words["{number}. {title}"].format(number=section.number, title=section.title), rtl)


def contents(sections, page_numbers, words, rtl):
    links = []
    for section in sections:
        title = section_title(section, words, rtl)
        if rtl:
            title = f"<span>{title}</span>"
        number = page_numbers[section.number]
        label = escape(words["PDF page {number}"].format(number=number))
        links.append(f'<li><a href="#section-{section.number}">{title}'
                     f' <span class="page" aria-label="{label}">{number}</span></a></li>')
    rows = (len(sections) + 1) // 2
    extra_rows = f' style="--contents-rows:{rows}"' if rows > 5 else ""
    heading = escape(words["Contents"])
    return (f'<nav class="contents" aria-labelledby="contents"><h2 id="contents">{heading}</h2>'
            f'<ol{extra_rows}>{"".join(links)}</ol></nav>')


def cover(model, page_numbers, words, rtl):
    frame = escape(model.choice["frame"])
    position = escape(model.choice["name_position"])
    summaries = "".join(f"<p>{inline(text, rtl)}</p>" for text in model.cover_summary)
    panels = "".join(
        f'<div class="cover-block"><h3>{inline(section.title, rtl)}</h3>'
        + "".join(block_html(block, words, rtl) for block in section.blocks) + "</div>"
        for section in model.cover_blocks
    )
    details = description_list(model.details, f'details {model.choice["details_style"]}', rtl)
    return (
        f'<header class="cover {frame}"><div class="cover-heading {position}">'
        f'<h1>{inline(model.name, rtl)}</h1><p class="doc-title">{inline(model.title, rtl)}</p>{summaries}</div>'
        f'{metrics(model.metrics, rtl)}{contents(model.sections, page_numbers, words, rtl)}'
        f'<div class="cover-blocks">{panels}</div>{details}</header>'
    )


def render_document(model, theme, page_numbers):
    words = load(model.language)
    rtl = model.direction == "rtl"
    sections = "".join(
        f'<section id="section-{section.number}"><h2>{section_title(section, words, rtl)}</h2>'
        + "".join(block_html(block, words, rtl) for block in section.blocks) + "</section>"
        for section in model.sections
    )
    credit_direction = ' dir="ltr"' if rtl else ""
    credit = f'<p class="credit"{credit_direction}>{escape(model.credit)}</p>' if model.credit else ""
    page_title = f"{model.name} | {model.title}"
    design = for_language(theme, model.language)
    html = (
        '<!doctype html>\n'
        f'<html lang="{escape(model.language)}" dir="{escape(model.direction)}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{escape(display(page_title) if rtl else page_title)}</title><style>{styles(design)}</style></head>'
        f'<body><main><p class="official">{escape(words["The PDF is the official copy."])}</p>'
        f'{cover(model, page_numbers, words, rtl)}{sections}<footer><div><span>{inline(model.title, rtl)}</span>'
        f'<span>{escape(words["Confidential"])}</span></div>{credit}</footer></main></body></html>\n'
    )
    return html.encode("utf-8")
