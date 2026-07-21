import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// Renders the small HTML subset produced by the admin panel's legal-document
/// editor (h1, h2, p, ul/ol/li, b/strong, i/em, u, a, br) as native Flutter
/// widgets, instead of showing the raw tags as literal text.
///
/// This is a deliberately minimal hand-rolled parser rather than a
/// full HTML-rendering package — the content is always authored through our
/// own admin RichTextEditor, which only ever emits this exact tag set, so a
/// general-purpose HTML engine (and its dependency weight) isn't needed.
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
        return RichText(text: TextSpan(style: h1, children: _parseInline(block.text, h1, link)));
      case _BlockType.h2:
        return RichText(text: TextSpan(style: h2, children: _parseInline(block.text, h2, link)));
      case _BlockType.listItem:
        return Padding(
          padding: const EdgeInsets.only(left: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(block.ordinal != null ? '${block.ordinal}. ' : '•  ', style: body),
              Expanded(child: RichText(text: TextSpan(style: body, children: _parseInline(block.text, body, link)))),
            ],
          ),
        );
      case _BlockType.paragraph:
        return RichText(text: TextSpan(style: body, children: _parseInline(block.text, body, link)));
    }
  }

  static List<_Block> _parseBlocks(String rawHtml) {
    final blocks = <_Block>[];
    // Strip whitespace between tags so stray newlines from the source don't
    // turn into spurious paragraphs.
    final src = rawHtml.trim();
    if (src.isEmpty) return blocks;

    final blockTag = RegExp(
      r'<h1[^>]*>(.*?)</h1>|<h2[^>]*>(.*?)</h2>|<ul[^>]*>(.*?)</ul>|<ol[^>]*>(.*?)</ol>|<p[^>]*>(.*?)</p>',
      caseSensitive: false,
      dotAll: true,
    );

    var lastEnd = 0;
    for (final m in blockTag.allMatches(src)) {
      // Any bare text between recognized block tags (content not wrapped in
      // a tag at all) becomes its own paragraph, so nothing silently vanishes.
      final between = src.substring(lastEnd, m.start).trim();
      if (between.isNotEmpty) blocks.add(_Block(_BlockType.paragraph, between));
      lastEnd = m.end;

      if (m.group(1) != null) {
        blocks.add(_Block(_BlockType.h1, m.group(1)!.trim()));
      } else if (m.group(2) != null) {
        blocks.add(_Block(_BlockType.h2, m.group(2)!.trim()));
      } else if (m.group(3) != null || m.group(4) != null) {
        final isOrdered = m.group(4) != null;
        final listInner = (m.group(3) ?? m.group(4))!;
        final liTag = RegExp(r'<li[^>]*>(.*?)</li>', caseSensitive: false, dotAll: true);
        var n = 1;
        for (final li in liTag.allMatches(listInner)) {
          blocks.add(_Block(_BlockType.listItem, li.group(1)!.trim(), ordinal: isOrdered ? n : null));
          n++;
        }
      } else if (m.group(5) != null) {
        blocks.add(_Block(_BlockType.paragraph, m.group(5)!.trim()));
      }
    }
    final tail = src.substring(lastEnd).trim();
    if (tail.isNotEmpty) blocks.add(_Block(_BlockType.paragraph, tail));

    return blocks;
  }

  static List<InlineSpan> _parseInline(String text, TextStyle base, Color linkColor) {
    final spans = <InlineSpan>[];
    final inlineTag = RegExp(
      r'<(b|strong|i|em|u|a)(?:\s+href="([^"]*)")?[^>]*>(.*?)</\1>|<br\s*/?>',
      caseSensitive: false,
      dotAll: true,
    );

    var lastEnd = 0;
    for (final m in inlineTag.allMatches(text)) {
      final before = text.substring(lastEnd, m.start);
      if (before.isNotEmpty) spans.add(TextSpan(text: _unescape(before)));
      lastEnd = m.end;

      final tag = m.group(1)?.toLowerCase();
      if (tag == null) {
        // <br>
        spans.add(const TextSpan(text: '\n'));
        continue;
      }
      final inner = m.group(3) ?? '';
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
          final href = m.group(2);
          spans.add(TextSpan(
            text: _unescape(_stripTags(inner)),
            style: base.copyWith(color: linkColor, decoration: TextDecoration.underline),
            recognizer: href != null
                ? (TapGestureRecognizer()..onTap = () => launchUrl(Uri.parse(href), mode: LaunchMode.externalApplication))
                : null,
          ));
          break;
      }
    }
    final rest = text.substring(lastEnd);
    if (rest.isNotEmpty) spans.add(TextSpan(text: _unescape(rest)));
    return spans;
  }

  static String _stripTags(String s) => s.replaceAll(RegExp(r'<[^>]+>'), '');

  static String _unescape(String s) => s
      .replaceAll('&nbsp;', ' ')
      .replaceAll('&amp;', '&')
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>')
      .replaceAll('&quot;', '"')
      .replaceAll('&#39;', "'");
}

enum _BlockType { h1, h2, paragraph, listItem }

class _Block {
  final _BlockType type;
  final String text;
  final int? ordinal;
  _Block(this.type, this.text, {this.ordinal});
}
