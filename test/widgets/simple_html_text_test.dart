import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/widgets/simple_html_text.dart';

/// Collects the plain text actually rendered by a SimpleHtmlText tree, so
/// tests can assert on what a user would see rather than on internal
/// widget structure.
String renderedText(WidgetTester tester) {
  final richTexts = tester.widgetList<RichText>(find.byType(RichText));
  return richTexts.map((rt) => rt.text.toPlainText()).join('\n');
}

Future<void> pumpHtml(WidgetTester tester, String html) {
  return tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: SimpleHtmlText(html)),
    ),
  );
}

void main() {
  group('SimpleHtmlText', () {
    testWidgets('renders <div>-wrapped paragraphs without leaking the tags', (tester) async {
      // This is exactly what Chrome's contentEditable produces for plain
      // typed paragraphs (RichTextEditor.jsx never sets
      // defaultParagraphSeparator to 'p'), so it must render as normal text,
      // not literal <div> markup.
      await pumpHtml(tester, '<div>First paragraph.</div><div>Second paragraph.</div>');

      final text = renderedText(tester);
      expect(text, contains('First paragraph.'));
      expect(text, contains('Second paragraph.'));
      expect(text, isNot(contains('<div>')));
      expect(text, isNot(contains('</div>')));
    });

    testWidgets('renders mixed div/p/heading/list content correctly', (tester) async {
      await pumpHtml(tester, '''
        <h2>Section Title</h2>
        <div>An intro paragraph with <strong>bold text</strong> in it.</div>
        <ul><li>First item</li><li>Second item</li></ul>
        <p>A proper paragraph too.</p>
      ''');

      final text = renderedText(tester);
      expect(text, contains('Section Title'));
      expect(text, contains('An intro paragraph with'));
      expect(text, contains('bold text'));
      expect(text, contains('First item'));
      expect(text, contains('Second item'));
      expect(text, contains('A proper paragraph too.'));
      expect(text, isNot(contains('<')));
    });

    testWidgets('strips unrecognized tags instead of showing them literally', (tester) async {
      // Defends against other browser/editor quirks (e.g. Safari emitting
      // <span style="..."> for some commands) beyond the specific <div> case.
      await pumpHtml(tester, '<div>Some <span style="color:red">styled</span> text.</div>');

      final text = renderedText(tester);
      expect(text, contains('Some'));
      expect(text, contains('styled'));
      expect(text, contains('text.'));
      expect(text, isNot(contains('<span')));
    });

    testWidgets('still renders a clean <p>-only document (no regression)', (tester) async {
      await pumpHtml(tester, '<h1>Title</h1><p>Body copy.</p>');

      final text = renderedText(tester);
      expect(text, contains('Title'));
      expect(text, contains('Body copy.'));
    });

    testWidgets('unescapes smart-quote/dash entities from pasted rich text', (tester) async {
      await pumpHtml(tester, '<p>It&rsquo;s the vendor&rsquo;s choice &mdash; &ldquo;great&rdquo; &hellip;</p>');

      final text = renderedText(tester);
      expect(text, contains('It’s the vendor’s choice — “great” …'));
      expect(text, isNot(contains('&')));
    });

    testWidgets('accepts single-quoted href attributes', (tester) async {
      await pumpHtml(tester, "<p>See <a href='https://example.com'>this link</a>.</p>");

      final text = renderedText(tester);
      expect(text, contains('this link'));

      final richTexts = tester.widgetList<RichText>(find.byType(RichText));
      final hasRecognizer = richTexts.any((rt) {
        final span = rt.text;
        var found = false;
        span.visitChildren((s) {
          if (s is TextSpan && s.recognizer != null) found = true;
          return true;
        });
        return found;
      });
      expect(hasRecognizer, isTrue);
    });

    testWidgets('does not attach a tap recognizer for an empty href', (tester) async {
      await pumpHtml(tester, '<p>See <a href="">this link</a>.</p>');

      final richTexts = tester.widgetList<RichText>(find.byType(RichText));
      final hasRecognizer = richTexts.any((rt) {
        final span = rt.text;
        var found = false;
        span.visitChildren((s) {
          if (s is TextSpan && s.recognizer != null) found = true;
          return true;
        });
        return found;
      });
      expect(hasRecognizer, isFalse);
    });
  });
}
