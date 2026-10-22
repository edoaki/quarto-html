"""Integration checks use the actual generated HTML and a disposable deck."""
import argparse
import importlib.util
import shutil
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('slides',ROOT/'scripts/slides.py')
slides=importlib.util.module_from_spec(spec);spec.loader.exec_module(slides)

class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name='workflow-test'
        if (ROOT/'decks'/cls.name).exists():raise RuntimeError('Test destination exists')
        slides.create_deck(argparse.Namespace(name=cls.name,source=None))
        cls.folder=ROOT/'decks'/cls.name
        (cls.folder/'images/mark.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><circle cx="20" cy="20" r="15" fill="red"/></svg>')
        (cls.folder/'slides.qmd').write_text('''---
title: Workflow
---
## First

![Local image](images/mark.svg)

<div data-step="1">Next step</div>

## Second

<iframe src="../../html/pomo/index.html" title="POMO"></iframe>

## Third

End.
''')
        cls.output=slides.render(cls.name)
        cls.p=sync_playwright().start();cls.browser=cls.p.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.p.stop()
        shutil.rmtree(cls.folder);shutil.rmtree(ROOT/'.build'/cls.name)
        cls.output.unlink()

    def page(self):
        page=self.browser.new_page(viewport={'width':1280,'height':720})
        page.goto(self.output.as_uri());page.wait_for_function('window.deckReady');return page

    def test_no_chapters_and_image_embedding(self):
        page=self.page();page.click('#menu')
        self.assertEqual(page.locator('.overview-grid').count(),1)
        self.assertEqual(page.locator('.thumb').count(),3)
        self.assertEqual(len(page.locator('.overview-grid').evaluate('e=>getComputedStyle(e).gridTemplateColumns.split(" ")')),4)
        self.assertTrue(page.locator('img').get_attribute('src').startswith('data:image/svg+xml'))
        self.assertTrue(page.locator('img').evaluate('e=>e.complete&&e.naturalWidth>0'))
        page.close()

    def test_step_boundaries_and_hash(self):
        page=self.page();self.assertFalse(page.locator('[data-step]').is_visible())
        page.keyboard.press('ArrowRight');self.assertTrue(page.locator('[data-step]').is_visible())
        page.keyboard.press('ArrowRight');self.assertEqual(page.evaluate('deck.index'),1)
        page.keyboard.press('ArrowLeft');self.assertEqual(page.evaluate('[deck.index,deck.step]'),[0,1])
        page.evaluate('deck.go(1,3)');page.reload();page.wait_for_function('window.deckReady')
        self.assertEqual(page.evaluate('[deck.index,deck.step]'),[1,3]);page.close()

    def test_copy_is_independent_and_no_overwrite(self):
        dest='workflow-copy'
        try:
            slides.create_deck(argparse.Namespace(name=dest,source=self.name))
            copied=ROOT/'decks'/dest/'slides.qmd'
            self.assertEqual(copied.read_text(),(self.folder/'slides.qmd').read_text())
            copied.write_text('changed')
            self.assertNotEqual(copied.read_text(),(self.folder/'slides.qmd').read_text())
            with self.assertRaises(ValueError):slides.create_deck(argparse.Namespace(name=dest,source=None))
        finally:shutil.rmtree(ROOT/'decks'/dest,ignore_errors=True)

    def test_webkit_mobile_taps(self):
        if not Path(self.p.webkit.executable_path).exists():
            self.skipTest('Optional: uv run playwright install webkit')
        browser=self.p.webkit.launch()
        try:
            context=browser.new_context(**self.p.devices['iPhone 13'])
            page=context.new_page();page.goto(self.output.as_uri());page.wait_for_function('window.deckReady')
            page.evaluate('deck.go(1)');box=page.locator('#stage').bounding_box()
            page.touchscreen.tap(box['x']+box['width']*.7,box['y']+box['height']*.5)
            page.wait_for_function('deck.step === 1')
            page.touchscreen.tap(box['x']+box['width']*.1,box['y']+box['height']*.5)
            page.wait_for_function('deck.step === 0')
            page.locator('#menu').tap();self.assertTrue(page.locator('#overview').is_visible())
        finally:browser.close()

    def test_missing_resource_fails(self):
        from bs4 import BeautifulSoup
        with self.assertRaises(FileNotFoundError):slides.bundle(BeautifulSoup('<img src="images/missing.png">','html.parser'),self.folder)
        with self.assertRaises(ValueError):slides.bundle(BeautifulSoup('<script src="https://example.com/no.js"></script>','html.parser'),self.folder)

if __name__=='__main__':unittest.main()
