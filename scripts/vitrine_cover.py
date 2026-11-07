"""Deterministic, professional SVG covers for all Git repository types.

No image-generation model or external assets. A cover is branded graphic art,
NOT a fake screenshot. Private-source covers deliberately look just as good
as public-source covers.
"""
from __future__ import annotations
import hashlib
import html
import math
import textwrap

PALETTES = (
    ("#101a2a","#233d52","#f2b981","#79d8cc"),
    ("#101b20","#284d46","#e7c991","#8ee1b9"),
    ("#181628","#47375b","#e7a7bf","#a1b4ee"),
    ("#17202b","#364b60","#d7b98e","#8ecbfa"),
    ("#201a24","#4b3348","#f4bc92","#b8a9e7"),
    ("#11222b","#1e4d56","#e4d2a2","#82dae0"),
)

def cover(name: str, version: str, mode: str = "diagram",
          visibility: str = "public", category: str = "SOFTWARE") -> str:
    """Create an author-previewable 1280×720 SVG graphic."""
    seed=int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8],16)
    dark, medium, gold, aqua=PALETTES[seed%len(PALETTES)]
    # Keep text inside card and show up to two clean title lines.
    source=" ".join(str(name).strip().split()) or "Untitled project"
    lines=textwrap.wrap(source,width=27,break_long_words=True,break_on_hyphens=True)[:2] or ["Untitled"]
    if len(lines)==2 and len(lines[1])>=27:lines[1]=lines[1][:25]+"…"
    rendered_title="".join(
        '<text x="102" y="'+str(289+i*76)+'" fill="#f6f3ee" font-size="'+
        ("65" if max(map(len,lines))<=24 else "55")+
        '" font-weight="700" font-family="Arial,DejaVu Sans,sans-serif">'+html.escape(line)+'</text>'
        for i,line in enumerate(lines)
    )
    version_label=html.escape(str(version)[:40] or "—")
    category_label=html.escape(str(category).upper()[:38])
    # A few deliberate geometric compositions; never a simulated app UI.
    kind=seed%4
    motifs=[]
    if kind==0:
        for r in (85,150,222,310):
            motifs.append(f'<circle cx="1010" cy="358" r="{r}" fill="none" stroke="{aqua}" stroke-opacity=".25" stroke-width="2"/>')
        motifs.append(f'<circle cx="1010" cy="358" r="65" fill="{aqua}" fill-opacity=".17"/>')
        for i in range(8):
            a=i*math.pi/4+seed%7/11
            x1=1010+math.cos(a)*110;y1=358+math.sin(a)*110
            x2=1010+math.cos(a)*285;y2=358+math.sin(a)*285
            motifs.append(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{gold}" stroke-opacity=".3" stroke-width="1.6"/>')
    elif kind==1:
        for i in range(8):
            t=i*35
            motifs.append(f'<path d="M{810+t} 98L{1180+t} 460L{960+t} 680" fill="none" stroke="{aqua}" stroke-opacity="{.05+i*.036:.3f}" stroke-width="3"/>')
        motifs.append(f'<path d="M880 440L1050 260L1190 405L1020 580Z" fill="{gold}" fill-opacity=".1" stroke="{gold}" stroke-opacity=".38" stroke-width="3"/>')
    elif kind==2:
        for i in range(7):
            s=105+i*57
            motifs.append(f'<rect x="{815-i*12}" y="{s}" width="{260+i*25}" height="{100+i*26}" rx="{18+i*2}" fill="none" stroke="{aqua}" stroke-opacity="{.31-i*.035:.3f}" stroke-width="2"/>')
        motifs.append(f'<circle cx="1080" cy="354" r="38" fill="{gold}" fill-opacity=".28"/>')
    else:
        for i in range(10):
            y=140+i*46
            off=(i%3)*30
            motifs.append(f'<path d="M{840+off} {y}Q1085 {y-80} 1260 {y-20}" fill="none" stroke="{aqua}" stroke-opacity="{.15+i*.02:.3f}" stroke-width="2"/>')
        for i in range(12):
            a=i*math.pi/6
            cx=1070+math.cos(a)*160;cy=360+math.sin(a)*160
            motifs.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{gold}" opacity=".55"/>')
    label="В РАЗРАБОТКЕ" if mode=="development" else "PRODUCT / SOURCE CODE PRIVATE" if visibility=="private" else "PRODUCT / OPEN SOURCE"
    # Neutral source visibility in the visual language: no warning or shame badge.
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img" '
            'aria-label="Фирменная обложка проекта '+html.escape(source,quote=True)+'">'
            '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="'+dark+'"/>'
            '<stop offset="1" stop-color="'+medium+'"/></linearGradient>'
            '<radialGradient id="glow"><stop stop-color="'+aqua+'" stop-opacity=".16"/>'
            '<stop offset="1" stop-color="'+aqua+'" stop-opacity="0"/></radialGradient></defs>'
            '<rect width="1280" height="720" fill="url(#bg)"/>'
            '<circle cx="1040" cy="330" r="450" fill="url(#glow)"/>'
            '<path d="M0 115H1280M0 610H1280" stroke="#ffffff" stroke-opacity=".12"/>'
            '<path d="M68 0V720M1212 0V720" stroke="#ffffff" stroke-opacity=".07"/>'
            +''.join(motifs)+
            '<rect x="102" y="80" width="59" height="59" rx="13" fill="'+gold+'"/>'
            '<text x="113" y="120" fill="'+dark+'" font-size="25" font-weight="800" font-family="Arial,DejaVu Sans,sans-serif">PL</text>'
            '<text x="181" y="102" fill="'+gold+'" font-size="15" font-family="DejaVu Sans,Arial,sans-serif" letter-spacing="3">PL CODE STORE</text>'
            '<text x="181" y="123" fill="#c6d4d9" font-size="12" font-family="DejaVu Sans,Arial,sans-serif" letter-spacing="2">PRODUCT VITRINE / '+category_label+'</text>'
            +rendered_title+
            '<rect x="102" y="465" width="210" height="46" rx="23" fill="'+gold+'" fill-opacity=".15" stroke="'+gold+'" stroke-opacity=".45"/>'
            '<text x="124" y="495" fill="'+gold+'" font-size="18" font-weight="600" font-family="DejaVu Sans,Arial,sans-serif">VERSION '+version_label+'</text>'
            '<text x="102" y="579" fill="#c4d3dc" font-size="17" font-family="DejaVu Sans,Arial,sans-serif">'+html.escape(label)+'</text>'
            '<text x="102" y="647" fill="#8298a8" font-size="14" font-family="DejaVu Sans,Arial,sans-serif" letter-spacing="2">DESIGNED FROM VERIFIED METADATA  /  NOT A SCREENSHOT</text>'
            '<path d="M1120 625H1174M1147 598V652" stroke="'+gold+'" stroke-width="3" stroke-opacity=".65"/>'
            '</svg>')
