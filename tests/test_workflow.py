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
        self.assertEqual(page.locator('.references-slide').count(),0)
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

    def test_bibliography_default_and_explicit_heading(self):
        from bs4 import BeautifulSoup
        name='bibliography-test'
        folder=ROOT/'decks'/name
        self.assertFalse(folder.exists())
        slides.create_deck(argparse.Namespace(name=name,source=None))
        try:
            (folder/'reference.bib').write_text('\n'.join('@book{r%d, author={Writer, A}, title={Book %d}, year={2020}}'%(i,i) for i in range(7)))
            source='## Content\n\n'+ '; '.join('[@r%d]'%i for i in range(7))+'\n'
            for heading in ('','\n## 参考文献 {#references}\n'):
                (folder/'slides.qmd').write_text(source+heading)
                doc=BeautifulSoup(slides.render(name).read_text(),'html.parser')
                self.assertEqual(len(doc.select('.references-slide')),2)
                self.assertEqual(len(doc.select('.references-slide .csl-entry')),7)
                self.assertEqual(len(doc.select('.slide')),3)
                self.assertEqual(len(doc.select('.citations p')),7)
        finally:
            shutil.rmtree(folder);shutil.rmtree(ROOT/'.build'/name,ignore_errors=True)
            (ROOT/'output'/f'{name}.html').unlink(missing_ok=True)

    def test_retained_svg_animation(self):
        page=self.browser.new_page()
        page.goto((ROOT/'output/nco-intro.html').as_uri());page.wait_for_function('window.deckReady')
        page.evaluate("deck.go([...document.querySelectorAll('.slide')].findIndex(s=>s.id==='background'))")
        frame=page.locator('#background iframe').content_frame
        frame.locator('svg').evaluate('e=>window.originalSvg=e')
        before=frame.locator('svg').inner_html()
        frame.locator('svg').evaluate('()=>{window.animation.setStep(1,true)}')
        page.wait_for_timeout(120)
        intermediate=frame.locator('svg').inner_html()
        frame.locator('svg').evaluate('async()=>await window.animation.settled')
        final=frame.locator('svg').inner_html()
        self.assertNotEqual(before,intermediate);self.assertNotEqual(intermediate,final)
        self.assertTrue(frame.locator('svg').evaluate('e=>e===window.originalSvg'))
        page.close()

    def test_footer_number_is_above_rule(self):
        page=self.browser.new_page(viewport={'width':1280,'height':720})
        page.goto((ROOT/'output/nco-intro.html').as_uri());page.wait_for_function('window.deckReady')
        for i in range(page.evaluate('deck.count')):
            page.evaluate('(i)=>deck.go(i)',i)
            gap=page.evaluate("""() => {
                const s=document.querySelector('.slide.active'),r=s.getBoundingClientRect(),scale=r.width/1280;
                const line=r.bottom-parseFloat(getComputedStyle(s,'::after').bottom)*scale;
                return line-s.querySelector('.page-number').getBoundingClientRect().bottom;
            }""")
            self.assertGreater(gap,6)
        page.emulate_media(media='print');page.evaluate("document.body.classList.add('export');deck.go(2)")
        self.assertTrue(page.locator('#background iframe').is_visible())
        page.close()

    def example_page(self, slide_id):
        page=self.browser.new_page(viewport={'width':1280,'height':720})
        page.goto((ROOT/'output/nco-intro.html').as_uri());page.wait_for_function('window.deckReady')
        page.evaluate('(id)=>deck.go([...document.querySelectorAll(".slide")].findIndex(s=>s.id===id))',slide_id)
        return page

    def test_learning_model_transfer_and_route_timing(self):
        page=self.example_page('nco')
        frame=page.locator('#nco iframe').element_handle().content_frame()
        self.assertEqual(frame.locator('[data-key="model-inf"]').count(),0)
        self.assertEqual(frame.locator('[data-key="answer"]').count(),0)
        self.assertEqual(frame.locator('[data-key="train-0-e0"]').count(),0)
        frame.evaluate('animation.setStep(1,false)')
        timing=frame.evaluate("""async()=>{
          const samples=[];let done=false;
          animation.setStep(2,true).then(()=>done=true);
          while(!done){samples.push([
            !!document.querySelector('[data-key="arrow-make"]'),
            !!document.querySelector('[data-key="train-0-e0"]')]);
            await new Promise(requestAnimationFrame);}
          return samples;
        }""")
        self.assertTrue(all(a==b for a,b in timing))
        frame.evaluate('animation.setStep(3,false)')
        positions=frame.evaluate("""async()=>{
          const samples=[];let done=false;
          animation.setStep(4,true).then(()=>done=true);
          while(!done){const g=document.querySelector('[data-key="model-inf"]');
            if(g){const m=g.transform.baseVal.consolidate().matrix;samples.push([m.e,m.f]);}
            await new Promise(requestAnimationFrame);}
          return samples;
        }""")
        self.assertTrue(any(210<x<770 and abs(y-330)<.1 for x,y in positions))
        self.assertTrue(any(abs(x-780)<.1 and 195<y<325 for x,y in positions))
        self.assertTrue(all(abs(y-330)<.1 or abs(x-780)<.1 for x,y in positions))
        frame.evaluate('animation.setStep(6,false)')
        self.assertGreater(frame.locator('[data-key="answer"] line').count(),0)
        frame.evaluate('animation.setStep(0,false)')
        self.assertEqual(frame.locator('[data-key="model-inf"]').count(),0)
        page.close()

    def test_processing_labels_stay_opaque_during_motion(self):
        page=self.example_page('background')
        result=page.locator('#background iframe').content_frame.locator('svg').evaluate("""async () => {
            await animation.setStep(1,false);
            let running=true,samples=0,minOpacity=1,missing=0;
            const completion=animation.setStep(2,true).then(()=>running=false);
            while(running){
                const ops=[...document.querySelectorAll('[data-key^="op-"]')];
                for(const op of ops){const label=op.querySelector('text');if(!label){missing++;continue;}
                    let alpha=1;for(let el=label;el&&el!==op.parentElement;el=el.parentElement)alpha*=Number(getComputedStyle(el).opacity);
                    minOpacity=Math.min(minOpacity,alpha);
                }
                samples++;await new Promise(requestAnimationFrame);
            }
            await completion;return {samples,minOpacity,missing};
        }""")
        self.assertGreater(result['samples'],20)
        self.assertEqual(result['missing'],0)
        self.assertEqual(result['minOpacity'],1)
        page.close()

    def test_heuristic_selection_and_route_begin_together(self):
        page=self.example_page('heuristic')
        result=page.locator('#heuristic iframe').content_frame.locator('svg').evaluate("""async () => {
            await animation.setStep(0,false);
            let running=true,selectedAt=null,routeAt=null,tick=0;
            const completion=animation.setStep(1,true).then(()=>running=false);
            while(running){
                const chosen=document.querySelector('[data-key^="dist-"] rect[fill="#ae641a"]');
                const edge=document.querySelector('[data-key^="route-"] line');
                if(chosen&&selectedAt===null)selectedAt=tick;
                if(edge&&routeAt===null)routeAt=tick;
                tick++;await new Promise(requestAnimationFrame);
            }
            await completion;return {selectedAt,routeAt};
        }""")
        self.assertIsNotNone(result['selectedAt'])
        self.assertEqual(result['selectedAt'],result['routeAt'])
        page.close()

    def test_results_highlights_reverse_and_export(self):
        page=self.example_page('result-tsp')
        before=page.locator('#result-tsp table').inner_text()
        self.assertEqual(page.locator('#result-tsp .is-highlighted').count(),0)
        page.keyboard.press('ArrowRight')
        self.assertEqual(page.locator('#result-tsp .is-highlighted').all_text_contents(),['0.14%','0.04%'])
        page.keyboard.press('ArrowRight');self.assertEqual(page.locator('#result-tsp .is-highlighted').count(),4)
        page.keyboard.press('ArrowLeft');self.assertEqual(page.locator('#result-tsp .is-highlighted').count(),2)
        self.assertEqual(page.locator('#result-tsp table').inner_text(),before)
        page.evaluate('deck.jump(1)');page.emulate_media(media='print');page.evaluate("document.body.classList.add('export')")
        self.assertEqual(page.locator('#result-tsp .is-highlighted').count(),4)
        self.assertTrue(all(page.locator('#result-tsp .is-highlighted').nth(i).is_visible() for i in range(4)))
        page.close()

    def test_missing_resource_fails(self):
        from bs4 import BeautifulSoup
        with self.assertRaises(FileNotFoundError):slides.bundle(BeautifulSoup('<img src="images/missing.png">','html.parser'),self.folder)
        with self.assertRaises(ValueError):slides.bundle(BeautifulSoup('<script src="https://example.com/no.js"></script>','html.parser'),self.folder)

if __name__=='__main__':unittest.main()
