import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:html/dom.dart' as dom;
import 'package:html/parser.dart' as html_parser;
import 'package:url_launcher/url_launcher.dart';

/// Renders the small HTML subset produced by the admin panel's legal-document
/// editor (h1, h2, p, div, ul/ol/li, b/strong, i/em, u, a, br) as native
/// Flutter widgets, instead of showing the raw tags — or, worse, an entire
/// malformed document — as literal/misplaced text.
///
/// Block boundaries are found by walking a real parsed DOM tree (via
/// `package:html`, a pure-Dart HTML5 parser — no extra native dependency),
/// rather than a flat regex. That matters because admin-authored content is
/// never guaranteed clean: browsers wrap plain typed paragraphs in `<div>`
/// by default (RichTextEditor.jsx never sets defaultParagraphSeparator to
/// 'p'), and a native "select + copy" from a styled page can paste in with
/// heavy `<font>`/`<span style="...">` wrapping, or even end up nested
/// inside an unrelated block tag (e.g. an entire document accidentally
/// nested inside one stray `<h1>`). A flat regex has no way to tell where a
/// tag "really" ends in a document like that — it just matches the first
/// occurrence of the same closing tag, however far away — so a single
/// misplaced tag could swallow the rest of the document into one heading.
/// Walking the actual tree sidesteps that entirely: any element containing
/// block-level children is expanded into those children instead of being
/// treated as one leaf block, regardless of how deep or how mismatched the
/// nesting is.
///
/// Once a block's own boundary is found, its inner HTML is handed to a
/// small regex-based inline formatter for bold/italic/underline/links/line
/// breaks — that part of the original approach was never the problem, so
/// it's kept as-is. Presentation wrapper tags (font, span, and any other
/// unrecognized tag) are stripped rather than shown as literal text or
/// treated as their own block, so unexpected markup degrades gracefully.
class SimpleHtmlText extends StatelessWidget {
  final String html;
  final TextStyle? bodyStyle;
  final TextStyle? h1Style;
  final TextStyle? h2Style;
  final Color? linkColor;

  const SimpleHtmlText(
    this.html, {
    super.key,
    this.bodyStyle,
    this.h1Style,
    this.h2Style,
    this.linkColor,
  });

  @override
  Widget build(BuildContext context) {
    final body = bodyStyle ?? DefaultTextStyle.of(context).style;
    final h1 = h1Style ?? body.copyWith(fontSize: (body.fontSize ?? 14) + 8, fontWeight: FontWeight.w800);
    final h2 = h2Style ?? body.copyWith(fontSize: (body.fontSize ?? 14) + 4, fontWeight: FontWeight.w700);
    final link = linkColor ?? Theme.of(context).colorScheme.primary;

    final blocks = _parseBlocks(html);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (int i = 0; i < blocks.length; i++) ...[
          if (i > 0) SizedBox(height: blocks[i].type == _BlockType.listItem ? 4 : 14),
          _buildBlock(blocks[i], body: body, h1: h1, h2: h2, link: link),
        ],
      ],
    );
  }

  Widget _buildBlock(_Block block, {required TextStyle body, required TextStyle h1, required TextStyle h2, required Color link}) {
    switch (block.type) {
      case _BlockType.h1:
        return RichText(text: TextSpan(style: h1, children: _parseInline(block.innerHtml, h1, link)));
      case _BlockType.h2:
        return RichText(text: TextSpan(style: h2, children: _parseInline(block.innerHtml, h2, link)));
      case _BlockType.listItem:
        return Padding(
          padding: const EdgeInsets.only(left: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(block.ordinal != null ? '${block.ordinal}. ' : '•  ', style: body),
              Expanded(child: RichText(text: TextSpan(style: body, children: _parseInline(block.innerHtml, body, link)))),
            ],
          ),
        );
      case _BlockType.paragraph:
        return RichText(text: TextSpan(style: body, children: _parseInline(block.innerHtml, body, link)));
    }
  }

  // Tags that can legitimately contain further block-level structure. When a
  // candidate block element has one of these among its direct children, it's
  // expanded (recursed into) rather than treated as a single leaf block —
  // this is what correctly unwinds malformed/nested content instead of
  // swallowing it whole.
  static const _blockTags = {'h1', 'h2', 'p', 'div', 'blockquote', 'ul', 'ol'};

  static bool _hasBlockChild(dom.Element el) =>
      el.children.any((c) => _blockTags.contains(c.localName?.toLowerCase()));

  static List<_Block> _parseBlocks(String rawHtml) {
    final blocks = <_Block>[];
    final trimmed = rawHtml.trim();
    if (trimmed.isEmpty) return blocks;

    final document = html_parser.parse(trimmed);
    final root = document.body ?? document.documentElement;
    if (root == null) return blocks;

    void walk(dom.Node node) {
      if (node is dom.Text) {
        if (node.text.trim().isNotEmpty) {
          blocks.add(_Block(_BlockType.paragraph, node.text));
        }
        return;
      }
      if (node is! dom.Element) return;

      final tag = node.localName?.toLowerCase();
      switch (tag) {
        case 'h1':
        case 'h2':
          if (_hasBlockChild(node)) {
            for (final child in node.nodes) {
              walk(child);
            }
            return;
          }
          if (node.text.trim().isNotEmpty) {
            blocks.add(_Block(tag == 'h1' ? _BlockType.h1 : _BlockType.h2, node.innerHtml));
          }
          return;

        case 'ul':
        case 'ol':
          // Note: a <ul>/<ol> nested inside an <li> is not recursed into
          // here (only top-level li text), so it collapses into one
          // run-on line via _parseInline's tag-stripping instead of
          // rendering as its own nested list. No known admin-authored
          // content produces nested lists today; revisit if that changes.
          final ordered = tag == 'ol';
          var n = 1;
          for (final child in node.children) {
            if (child.localName?.toLowerCase() == 'li') {
              if (child.text.trim().isNotEmpty) {
                blocks.add(_Block(_BlockType.listItem, child.innerHtml, ordinal: ordered ? n : null));
              }
              n++;
            }
          }
          return;

        case 'p':
        case 'div':
        case 'blockquote':
          if (_hasBlockChild(node)) {
            for (final child in node.nodes) {
              walk(child);
            }
            return;
          }
          if (node.text.trim().isNotEmpty) {
            blocks.add(_Block(_BlockType.paragraph, node.innerHtml));
          }
          return;

        default:
          // Unrecognized element (font, span, body/html wrappers, or a
          // block-position inline tag like a bare top-level <b>) — not a
          // block itself, so recurse into its children rather than either
          // rendering it as a paragraph verbatim or dropping it.
          for (final child in node.nodes) {
            walk(child);
          }
          return;
      }
    }

    for (final child in root.nodes) {
      walk(child);
    }

    return blocks;
  }

  static List<InlineSpan> _parseInline(String text, TextStyle base, Color linkColor) {
    final spans = <InlineSpan>[];
    final inlineTag = RegExp(
      r'''<(b|strong|i|em|u|a)(?:\s+href=(["'])([^"']*)\2)?[^>]*>(.*?)</\1>|<br\s*/?>''',
      caseSensitive: false,
      dotAll: true,
    );

    var lastEnd = 0;
    for (final m in inlineTag.allMatches(text)) {
      final before = text.substring(lastEnd, m.start);
      if (before.isNotEmpty) spans.add(TextSpan(text: _unescape(_stripTags(before))));
      lastEnd = m.end;

      final tag = m.group(1)?.toLowerCase();
      if (tag == null) {
        // <br>
        spans.add(const TextSpan(text: '\n'));
        continue;
      }
      final inner = m.group(4) ?? '';
      switch (tag) {
        case 'b':
        case 'strong':
          spans.add(TextSpan(text: _unescape(_stripTags(inner)), style: base.copyWith(fontWeight: FontWeight.w700)));
          break;
        case 'i':
        case 'em':
          spans.add(TextSpan(text: _unescape(_stripTags(inner)), style: base.copyWith(fontStyle: FontStyle.italic)));
          break;
        case 'u':
          spans.add(TextSpan(text: _unescape(_stripTags(inner)), style: base.copyWith(decoration: TextDecoration.underline)));
          break;
        case 'a':
          final href = m.group(3);
          spans.add(TextSpan(
            text: _unescape(_stripTags(inner)),
            style: base.copyWith(color: linkColor, decoration: TextDecoration.underline),
            recognizer: href != null && href.isNotEmpty
                ? (TapGestureRecognizer()..onTap = () => launchUrl(Uri.parse(href), mode: LaunchMode.externalApplication))
                : null,
          ));
          break;
      }
    }
    final rest = text.substring(lastEnd);
    if (rest.isNotEmpty) spans.add(TextSpan(text: _unescape(_stripTags(rest))));
    return spans;
  }

  static String _stripTags(String s) => s.replaceAll(RegExp(r'<[^>]+>'), '');

  static String _unescape(String s) => s
      .replaceAll('&nbsp;', ' ')
      .replaceAll('&mdash;', '—')
      .replaceAll('&ndash;', '–')
      .replaceAll('&hellip;', '…')
      .replaceAll('&rsquo;', '’')
      .replaceAll('&lsquo;', '‘')
      .replaceAll('&rdquo;', '”')
      .replaceAll('&ldquo;', '“')
      .replaceAll('&amp;', '&')
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>')
      .replaceAll('&quot;', '"')
      .replaceAll('&#39;', "'");
}

enum _BlockType { h1, h2, paragraph, listItem }

class _Block {
  final _BlockType type;
  final String innerHtml;
  final int? ordinal;
  _Block(this.type, this.innerHtml, {this.ordinal});
}
