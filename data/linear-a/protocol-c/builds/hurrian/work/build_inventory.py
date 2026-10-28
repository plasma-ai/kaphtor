import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
rows = [[c.strip() for c in line.split('|')[1:-1]] for line in (ROOT/'units.md').read_text().splitlines() if line.startswith('| ')][1:]
labels = [r[2] if i < 30 else r[3] for i, r in enumerate(rows)]
sections = {2:'II.C.2',5:'II.C.2',8:'II.C.4',10:'II.C.4',11:'II.C.4',12:'II.C.4',13:'II.C.4, 12.',14:'II.C.4, 13.',15:'II.C.4, 14.',16:'II.C.4, 15.',17:'II.E',18:'II.E',30:'II.C.5',31:'II.C.5',32:'II.C.5'}
entries = []
seen = {}
coverage = defaultdict(set)
attestations = defaultdict(list)
N='nominal'; P='pronominal'; V='verbal'; C='clitic'
ST='s_stem'; GN='s_gender_number'; CP='s_case_person'; PR='s_pronoun'; EN='s_enclitic'

def add(u, m, cat, slot, form, sounds, function, page=None, note=''):
    """Each supplied sound string is an expressly printed realization, not a generated allomorph."""
    if isinstance(sounds, str): sounds=[sounds]
    for sound in sounds:
        if not sound: continue
        seg=list(sound)
        key=(m,cat,slot,form,tuple(seg))
        source={'unit':labels[u], 'section':sections.get(u, rows[u][2]), 'page':str(page or rows[u][4])}
        if key in seen:
            idx=seen[key]
            if source != entries[idx]['source'] and source not in attestations[idx]:
                attestations[idx].append(source)
        else:
            idx=len(entries)
            seen[key]=idx
            e={'id':f'hurrian_{idx+1:03}', 'morpheme_id':'hurrian_'+m, 'category':cat, 'side':'suffix', 'slot':slot,
               'form':form, 'segments':seg, 'function':function, 'source':source}
            if note: e['notes']=note
            entries.append(e)
        coverage[u].add(idx)

def pron(u, person, form, sounds, page=None, note=''):
    names={'1sg':'1. Pers. Sg.', '2sg':'2. Pers. Sg.', '3sg':'3. Pers. Sg.', '1pl':'1. Pers. Pl.', '2pl':'2. Pers. Pl.', '3pl':'3. Pers. Pl.'}
    add(u,'encl_'+person,P,PR,form,sounds,'Enklitisches Personalpronomen des Absolutivs, '+names[person]+'; Subjekt- bzw. Objektanzeiger.',page,note)

def particle(u, form, sound, m=None, page=None):
    m=m or sound
    funcs={'an':'„und“; verbindet Wörter, Verben oder Sätze.', 'man':'„aber, eben o.ä.“', 'nin':'„fürwahr o.ä.“; steht immer am Wortende.', 'mmaman':'„und nämlich, und zwar“ oder ähnlich.', 'ma':'Etwa dieselbe Bedeutung wie -an; häufiger in Boğazköy.'}
    add(u,'assoc_'+m,C,EN,form,sound,'Enklitische Partikel (Assoziativ): '+funcs[m],page)

def v(u,m,form,sound,fn,slot=ST,page=None,note=''):
    add(u,m,V,slot,form,sound,fn,page,note)

# Possessivsuffixe: the list includes its plural continuation on p. 55.
for form,sound,cond in [('-iffə','iffə','Im Absolutiv und im absoluten Auslaut; ə bezeichnet unsichere Auslautung (Anm. 59).'),('-iffe','iffe','Im Absolutiv vor weiteren Suffixen.'),('-iff=u-','iffu','Mit Bindevokal -u- vor Genitiv, Dativ und wohl allen konsonantisch anlautenden Kasus.')]:
    add(0,'poss_1sg',P,PR,form,sound,'Enklitisches Possessiv-Pronomen, 1. Person Singular.',54,cond)
add(0,'poss_2sg',P,PR,'-v','v','Enklitisches Possessiv-Pronomen, 2. Person Singular.',55,'Themavokal bleibt erhalten.')
add(0,'poss_2sg',P,PR,'(-b/p)',['b','p'],'Enklitisches Possessiv-Pronomen, 2. Person Singular.',55,'In Klammern angegebene Varianten zu -v; keine fakultative Nullrealisierung gemeint.')
add(0,'poss_3sg',P,PR,'-i-','i','Enklitisches Possessiv-Pronomen, 3. Person Singular.',55,'Themavokal des Substantivs fällt weg.')
for m,form,sound in [('poss_1pl','-iff + aš','iffaš'),('poss_1pl','iffāš','iffāš'),('poss_2pl','-šu?','šu'),('poss_3pl','-i + aš','iaš'),('poss_3pl','iaš','iaš')]:
    add(0,m,P,PR,form,sound,'Enklitisches Possessiv-Pronomen, '+{'poss_1pl':'1.','poss_2pl':'2.','poss_3pl':'3.'}[m]+' Person Plural.',55,'Bei -šu? ist die Bestimmung unsicher; nur in der Bilingue belegt.' if m=='poss_2pl' else '')
add(0,'nom_plural',N,GN,'-aš-','aš','Plural des Possessiv-Suffixes und Plural vor Kasusmorphemen (außer im Absolutiv).',55)

# Entire case table, including fused plural-case strings and explicitly printed alternatives.
cases=[('article_pl','-(na)','na','Absolutiv Plural.',GN),('erg','-š','š','Ergativ Singular.',CP),('erg_pl','-aš=u=š','ašuš','Ergativ Plural.',CP),
('gen','-ve','ve','Genitiv Singular.',CP),('gen_pl','-aš=ve','ašve','Genitiv Plural; so nur in Nuzi.',CP),('gen_pl','aše','aše','Genitiv Plural; sonst.',CP),
('dat','-va','va','Dativ Singular.',CP),('dat_pl','-*aš=va','ašva','Dativ Plural; Ausgangsform der angegebenen Entwicklung.',CP),('dat_pl','aša','aša','Dativ Plural.',CP),
('dir','-t/da',['ta','da'],'Direktiv Singular.',CP),('dir','-u-da','uda','Direktiv Singular.',CP),('dir_pl','-aš=ta','ašta','Direktiv Plural.',CP),
('abl','-t/dan',['tan','dan'],'Ablativ Singular.',CP),('abl','-u-dan','udan','Ablativ Singular.',CP),('abl_pl','-aš=tan','aštan','Ablativ Plural.',CP),
('com','-ra','ra','Komitativ Singular.',CP),('com_pl','-aš=u=ra','ašura','Komitativ Plural.',CP),
('equ_adv','-nna','nna','Äquativ-Adverbialis Singular.',CP),('equ_adv_pl','-aš=u=nna','ašunna','Äquativ-Adverbialis Plural.',CP),
('equ_bog','-uš','uš','Äquativ (Boğ.).',CP),('instr','-ae','ae','Instrumental, auch adverbial.',CP),
('loc_instr','-ni/e?',['ni','ne'],'Lokativ-Instrumental (auch Abl.-Instr.); unsicher.',CP),('ess','-a','a','Essiv Singular.',CP),('ess_pl','-aš=a','aša','Essiv Plural.',CP),
('adv','-nni','nni','Adverbialis.',CP),('adv','-nnae','nnae','Adverbialis; aus -nn(i) + ae.',CP),('e_case','-e?','e','Kasus auf -e?; unsicher.',CP)]
for m,f,s,fn,slot in cases: add(1,m,N,slot,f,s,fn)
for m,forms,fn in [('gen',[('/fe/','fe'),('[ve]','ve'),('[we]','we')],'Genitiv; Lautung nach Anm. 65.'),('dat',[('/fa/','fa'),('[va]','va'),('[wa]','wa')],'Dativ; Lautung nach Anm. 66.')]:
    for f,s in forms: add(1,m,N,CP,f,s,fn,note='Grundlautung mit „wohl“ eingeschränkt; [v] nach Vokal, [w] nach u. Lautschrift der Tabellenfußnote.')

# Nominal chain tables. Nominal derivation in Wurzel+WEn is outside the listed categories.
for u in [2,5]:
    add(u,'article_sg',N,GN,'-ni','ni','Sog. „Artikel“, Singular.')
    add(u,'article_sg',N,GN,'/ne/','ne','Sog. „Artikel“, Singular; Lautung.')
    add(u,'article_pl',N,GN,'-na','na','Sog. „Artikel“, Plural.')
    add(u,'nom_plural',N,GN,'-aš-','aš','Pluralisator; auch Pluralität des Bezugswortes bei Suffixaufnahme.')
    for form,sound,m in [('-NE-','NE','relator_sg'),('-NA-','NA','relator_pl')]:
        add(u,m,N,GN,form,sound,'Suffixaufnahme; '+('Singular' if m.endswith('sg') else 'Plural')+' des Bezugswortes.',note='Kapitälchen der Tabelle als Großbuchstaben bewahrt; N und E/A sind einzelne Segmente, kein Decksymbol.')
    for m,f,s,fn in [('erg','-š','š','Ergativ des Bezugswortes.'),('gen','-ve','ve','Genitiv; auch Kasus des Bezugswortes.'),('dat','-va','va','Dativ des Bezugswortes.'),('dir','-ta','ta','Direktiv.')]: add(u,m,N,CP,f,s,fn)
    particle(u,'-an','an'); particle(u,'-man','man')
add(2,'gen',N,CP,'-ve-','ve','Genitiv, Position 4.')
add(2,'poss_1sg',P,PR,'-iff-u','iffu','Possessiv-Pronomen 1. Sg. mit Bindevokal.')
for person,form,sounds in [('1sg','-tta/t',['tta','t']),('2sg','-mma/m',['mma','m']),('3sg','-nna/n',['nna','n']),('1pl','-tilla/til',['tilla','til']),('2pl','-ffa/f',['ffa','f']),('3pl','-lla/l',['lla','l'])]: pron(2,person,form,sounds)
for m,f,s,fn in [('poss_1sg','-iffə','iffə','1. Sg.'),('poss_1sg','-iffe','iffe','1. Sg.'),('poss_1sg','-iff-','iff','1. Sg., vor Bindevokal.'),('poss_2sg','-v-','v','2. Sg.'),('poss_3sg','-i-','i','3. Sg.')]: add(5,m,P,PR,f,s,'Possessiv-Pronomen '+fn)
for person,form,sound in [('1sg','-tta','tta'),('2sg','-mma','mma'),('3sg','-nna','nna')]: pron(5,person,form,sound)

# Personal-pronoun table: phonetic variants are printed, not reconstructed.
for person,forms in [('1sg',[('-tta','tta'),('-t','t'),('[-d]','d')]),('2sg',[('-mma','mma'),('-m','m')]),('3sg',[('-nna','nna'),('-n','n')]),('1pl',[('-tilla','tilla'),('[-dilla]','dilla'),('-til','til'),('[-dil]','dil')]),('2pl',[('-ppa','ppa'),('[-ffa]','ffa'),('-p','p'),('[b/v]',['b','v'])]),('3pl',[('-lla','lla'),('-l','l')])]:
    for f,s in forms: pron(3,person,f,s,note='[-ffa]: so in der Boğ.-Bil. bezeugt.' if f=='[-ffa]' else '')

for f,s,m in [('-an','an','an'),('/man/','man','man'),('/mān/','mān','man'),('-nin','nin','nin'),('-mma-man','mmaman','mmaman')]: particle(4,f,s,m)

# Tense/aspect list and the positive subject-marker list.
v(6,'preterite','-oš-','oš','Präteritum; perfektiver Aspekt (beendete Handlung/Zustand).')
v(6,'future','-et-','et','Futur; imperfektiver Aspekt (nicht beendete Handlung/Zustand).')
for m,f,s,fn in [('agent_1sg','-av','av','1. Pers. Sg.'),('agent_1sg','-affu-','affu','1. Pers. Sg., Langform vor enkl. Pron. und nach Negationssuffix.'),('agent_2sg','-o','o','2. Pers. Sg.'),('agent_3sg','-a','a','3. Pers. Sg.'),('agent_1pl','-av + š(a)',['avš','avša'],'1. Pers. Pl.'),('agent_2pl','-aššu','aššu','2. Pers. Pl.; nur in der Boğ.-Bil.'),('agent_3pl','-a + š(a)',['aš','aša'],'3. Pers. Pl.'),('agent_3pl','-t + a','ta','3. Pers. Pl.')]:
    v(7,m,f,s,'Personenanzeiger (= Subjektanzeiger), transitiv-ergativisch positiv: '+fn,CP)
for f,s in [('-š','š'),('-ša','ša'),('-š(a)',['š','ša'])]: v(7,'verb_plural',f,s,'Pluralisator nach dem Personenanzeiger; -ša vor weiteren Formanten.',CP)
v(7,'verb_plural_t','-t-','t','Pluralisator; als Allophon von -id- anerkannt (Anm. 77).',CP)
v(7,'verb_plural_t','-id-','id','Pluralisator (Anm. 77).',CP)

# Verbal root-extension list.
root_forms=[('caus','-an(n)-',['an','ann'],'Kausativ.',75),('fact_am','-am-','am','Faktitiv.',76),('fact_iter_ar','-ar-','ar','Faktitiv und Iterativ.',76),('intens_as','-aš-','aš','Intensivierend o.ä.',76),('we_ahh','*-ahh-','ahh','Unklar; vielleicht räumliche Dimension „weg-“.',76),('recip_ukar','-uk+ar','ukar','Gegenseitigkeit; auch Iterativ-Durativ.',76),('recip_ukar','-ukar-','ukar','Gegenseitigkeit; auch Iterativ-Durativ.',76),('reflex_ul','-u/ol-',['ul','ol'],'Reflexiv, aber auch intransitivierend.',76),('we_ol','-ol-','ol','Unklar; vielleicht räumliche Beziehung „hin-“.',76),('we_om','-om-','om','Unklar.',76),('we_on','-on-','on','Unklar.',76),('we_Vst','-Všt-','Všt','Wurzelerweiterung; Vokal richtet sich nach dem Wurzelvokal; teils denominalisierend, vielleicht Aspekt/Aktionsart.',76),('inchoative','*-ill-','ill','Inchoativ oder Ingressiv; Eintritt oder Beginn eines Geschehens.',76),('we_us','-uš-','uš','Morphem unklarer Bedeutung; nicht der Tempusanzeiger.',76),('we_upp','-upp-','upp','Unklar.',77),('we_ut','-ut-','ut','Unklar; vielleicht in zul(l)=ud- und keb=ud-.',77),('we_t','-t-','t','Unklar; nicht Pluralmorphem oder Kennzeichen der Objektlosigkeit.',77),('we_uh','-uh/-oh',['uh','oh'],'Unklar.',77),('we_ur','*-o/ur-',['or','ur'],'Unklar.',77)]
for m,f,s,fn,p in root_forms: v(22,m,f,s,fn,page=p,note='Stern: nur im sog. „Althurritischen“.' if f.startswith('*') else '')
# Allomorphic root-extension shapes expressly exemplified in the itemised list.
for m,f,s,p in [('we_Vst','ašt-','ašt',76),('we_Vst','ešt-','ešt',76),('we_Vst','ušt-','ušt',76),('recip_ukar','ugar-','ugar',76),('we_ut','ud-','ud',77),('we_t','d-','d',77)]:
    v(22,m,f,s,'Realisierung der im Listeneintrag behandelten Wurzelerweiterung.',page=p,note='Affixteil der ausdrücklich segmentierten Beispiele im Listeneintrag; keine lexikalische Wurzel aufgenommen.')
v(22,'we_ut','-ud-','ud','Nach Anm. 76 möglicherweise Negativmorphem „ent-, los-, ab-“.',page=77,note='Abweichende Deutung zum Listeneintrag -ut-; nicht entschieden.')
v(22,'preterite','-uš-','uš','Tempusanzeiger; ausdrücklich vom gleichlautenden Wurzelerweiterungsmorphem unterschieden.',page=76)
v(22,'preterite','/oš/','oš','Lautung des im Listeneintrag genannten Tempusanzeigers -uš-.',page=76)

def common_chain(u, roots=True, tense=True, trans=True, encl=True, particles=True):
    if roots:
        for m,f,s in [('caus','-an-','an'),('fact_iter_ar','-ar-','ar'),('we_ol','-ol-','ol'),('we_Vst','-Všt-','Všt')]: v(u,m,f,s,'Wurzelerweiterung (Position 1).')
    if tense:
        v(u,'preterite','-oš-','oš','Tempus: Präteritum.')
        v(u,'future','-et-','et','Tempus: Futur.')
    if trans: v(u,'transitive','-i-','i','Kennzeichen der Transitivität (Position 5).')
    if encl:
        for person,f,s in [('1sg','-tta/t',['tta','t']),('2sg','-mma/m',['mma','m']),('3sg','-nna/n',['nna','n'])]: pron(u,person,f,s)
    if particles:
        particle(u,'-an','an'); particle(u,'-man','man')

common_chain(8)
for m,f,s,fn in [('agent_1sg','-av/-affu-',['av','affu'],'1. Sg.'),('agent_2sg','-o','o','2. Sg.'),('agent_3sg','-a','a','3. Sg.')]: v(8,m,f,s,'Kennzeichen des Subjekts der Handlung, '+fn,CP)
v(8,'verb_plural','-š(a-)',['š','ša'],'Kennzeichen der Pluralität des Subjekts.',CP)
v(8,'agent_3pl','t=a','ta','Alternative für die 3. Person Plural (Tabellenfußnote).',CP)
for m,f,s,fn in [('negative_1sg','-uffu','uffu','1. Sg.'),('negative_1pl','-uffu=š','uffuš','1. Pl.'),('negative_2pl','-uššu','uššu','2. Pl.')]: v(9,m,f,s,'Transitiv-ergativisch negativ, '+fn,CP)

common_chain(10)
v(10,'negative_trans','-u(w)/wa',['u','uw','wa'],'Kennzeichen der Negation, transitiv.')
v(10,'agent_1sg','+(a)ffu',['affu','ffu'],'Kennzeichen des Subjekts der Handlung, 1. Sg., nach Negation.',CP)
v(10,'agent_2pl','+(a)ššu',['aššu','ššu'],'Kennzeichen des Subjekts der Handlung, 2. Pl., nach Negation.',CP)
v(10,'negative_1sg','-uffu','uffu','1. Sg., Negation + Subjektanzeiger.',CP)
v(10,'negative_2pl','-uššu','uššu','2. Pl., Negation + Subjektanzeiger.',CP)
v(10,'verb_plural','-š(a-)',['š','ša'],'Kennzeichen der Pluralität des Subjekts.',CP)

# Intransitive and antipassive table.
for m,f,s in [('we_ol','-ol-','ol'),('we_Vst','-Všt-','Všt')]: v(11,m,f,s,'Wurzelerweiterung.')
common_chain(11,roots=False,trans=False,encl=False)
v(11,'objectless','-t-','t','Kennzeichen der Objektlosigkeit.')
for f,s in [('-a-','a'),('-o-','o')]: v(11,'intransitive',f,s,'Kennzeichen der Intransitivität; o ist ein Allophon von a.')
v(11,'negative_intrans','-kko','kko','Kennzeichen der Negation, intransitiv; eigentlich a, unterliegt der Vokalharmonie.',note='o > a vor -tta, -mma usw.; die Tabelle druckt keine selbständige Form -kka.')
v(11,'negative_intrans','-kki','kki','Negation beim Antipassiv.',note='i > a vor -tta, -mma usw.')
v(11,'transitive','-i-','i','Transitivität beim Antipassiv.')
for person,f,s in [('1sg','-tta/t',['tta','t']),('2sg','-mma/m',['mma','m']),('1pl','-tilla/til',['tilla','til']),('2pl','-ffa/f',['ffa','f']),('3pl','-lla/l',['lla','l'])]: pron(11,person,f,s,note='Hier als Subjektanzeiger; 3. Sg. ist ausdrücklich Null, nicht -nna.')

common_chain(12,encl=False)
for person,f,s in [('1sg','-tta/t',['tta','t']),('2sg','-mma/m',['mma','m'])]: pron(12,person,f,s)
for m,f,s,fn in [('objectless','-t-','t','Kennzeichen der Objektlosigkeit.'),('imbu','-imbu-','imbu','Position 4: unklar.'),('intransitive','-a-','a','Kennzeichen der Intransitivität.'),('negative_trans','-u(w)/wa-',['u','uw','wa'],'Kennzeichen der Negation.'),('negative_intrans','-kkV-','kkV','Kennzeichen der Negation; V ist ein Vokaldecksymbol.')]: v(12,m,f,s,fn)
v(12,'agent_1sg','-av/-(a)ffu-',['av','affu','ffu'],'Kennzeichen des Subjekts der Handlung, 1. Sg.',CP)
v(12,'agent_2sg','-o','o','Kennzeichen des Subjekts der Handlung, 2. Sg.',CP)
v(12,'agent_3sg','-a','a','Kennzeichen des Subjekts der Handlung, 3. Sg.',CP)
v(12,'verb_plural','-š(a-)',['š','ša'],'Kennzeichen der Pluralität des Subjekts.',CP)

# Positive and negative jussive tables.
for u in [13,14]:
    for m,f,s in [('caus','-an-' if u==13 else '-an','an'),('fact_iter_ar','-ar-','ar'),('intens_as','-aš-','aš'),('recip_ukar','-ugar-','ugar')]: v(u,m,f,s,'Wurzelerweiterung.')
    v(u,'jussive','-i-','i','Kennzeichen des Jussivs; vor Pluralisator und Personenanzeiger.')
    v(u,'jussive_3','-en','en','Personenanzeiger des Jussivs, 3. Person.',CP)
    particle(u,'-an','an')
v(13,'verb_plural_t','-(i)t-',['t','it'],'Pluralisator im positiven Jussiv.',CP)
v(13,'voluntative','-l+e','le','Personenanzeiger des Jussivs: Voluntativ, 1. Sg.',CP)
v(13,'imperative','-i/e',['i','e'],'Personenanzeiger des Jussivs: Imperativ, 2. Sg.',CP)
v(13,'verb_plural','-š(?)','š','Pluralisator, 1. Pl. des positiven Jussivs; unsicher.',CP,note='(?) ist ein Unsicherheitszeichen, kein fakultativer Laut.')
v(13,'imperative_pl','e+š(?)','eš','2. Pl. des positiven Jussivs; in der Spalte Pluralisator.',CP,note='(?) ist ein Unsicherheitszeichen.')
for person,f,s in [('1sg','-tta','tta'),('2sg','-mma','mma'),('3sg','-nna','nna'),('1pl','-tilla','tilla'),('2pl','-ffa','ffa'),('3pl','-lla','lla')]: pron(13,person,f,s,note='Die enklitischen Pronomina werden meist vorverlegt.')
v(14,'negative_trans','-wa-','wa','Kennzeichen der Negation im Jussiv.')
v(14,'verb_plural_t','(-id-)','id','Pluralisator des negierten Jussivs; eingeklammert.',CP,note='Tabellenfußnote: Ein negierter Jussiv in der 3. Pers. Pl. ist nicht belegt. Nur der gedruckte Formant wird aufgenommen.')
v(14,'voluntative','-l+e/-lli',['le','lli'],'Personenanzeiger des negierten Jussivs: Voluntativ.',CP)
pron(14,'3pl','-lla','lla'); particle(14,'-man','man')

# Optative and debitive-finalis tables.
v(15,'modal_ol','(-ol-)','ol','Formant vor -il- und -eva; fakultativ.')
for u in [15,16]:
    v(u,'modal_il','(-il-)','il','Formant des Optativs; fakultativ.')
    v(u,'verb_plural','-š(a)',['š','ša'],'Pluralisator des Handlungssubjekts.',CP)
    pron(u,'1sg','-tta','tta'); particle(u,'-an','an')
v(15,'conditional_opt','-eva','eva','Formant des konditionellen Optativs; Können oder Wollen.')
v(16,'debitive_final','-ae/-ai',['ae','ai'],'Formant des Debitiv-Finalis; Zweck oder Sollen.')
pron(16,'2sg','-mma','mma'); pron(16,'3sg','-nna','nna')

# Old verb table. Functions are taken only from the cells, not from adjacent prose.
for m,f,s,fn in [('fact_iter_ar','-ar','ar','Wurzelerweiterung.'),('we_Vst','-Všt-?','Všt','Wurzelerweiterung? Wahrscheinlich aber Aspekt/Aktionsart.'),('inchoative','-ill-','ill','Wurzelerweiterung? Wahrscheinlich aber Aspekt/Aktionsart.'),('we_ahh','-ahh-','ahh','Wurzelerweiterung? Wahrscheinlich aber Aspekt/Aktionsart.'),('reflex_ul','-ul-','ul','Wurzelerweiterung? Wahrscheinlich aber Aspekt/Aktionsart.'),('old_trans_o','-o','o','Kennzeichen transitiv-ergativisch.'),('transitive','-i','i','Kennzeichen transitiv-nicht ergativisch.'),('intransitive','-a','a','Kennzeichen intransitiv; auch bei Verben der Bewegung.'),('old_u','-u','u','Unklar, vielleicht bei intransitiven Handlungsverben.')]: v(17,m,f,s,fn)
v(17,'verb_plural_t','-id-','id','Kennzeichen der Pluralität.',CP)
v(17,'old_agent_m','-m','m','Subjektanzeiger: 3. Pers. Sg. Agens.',CP)
v(17,'old_subject_b','-b','b','Subjektanzeiger: 3. Person; bei -i und -a.',CP)
common_chain(18,roots=False,encl=False,particles=False)
v(18,'objectless','-t-','t','Position 3: Kennzeichen der Objektlosigkeit.')
v(18,'negative_trans','-u(w)/wa',['u','uw','wa'],'Kennzeichen der Negation.')
for m,f,s,fn in [('agent_1sg','-av/affu',['av','affu'],'1. Person'),('agent_2sg','-o','o','2. Person'),('agent_3sg','-a','a','3. Person')]: v(18,m,f,s,'Kennzeichen des Subjekts der Handlung, '+fn+'.',CP)
v(18,'verb_plural','-š(a)',['š','ša'],'Kennzeichen der Pluralität des Subjektes.',CP)

# Syntactic grids: equals signs are printed in the grids.
add(20,'erg',N,CP,'= š','š','Kasus Ergativ des Subjekts der Handlung (= Agens).')
v(20,'agent_1sg','= av/affu',['av','affu'],'Charakteristischer Personenanzeiger des transitiven Verbs, 1. Person.',CP)
v(20,'agent_2sg','= o','o','Charakteristischer Personenanzeiger des transitiven Verbs, 2. Person.',CP)
v(20,'agent_3sg','= a','a','Charakteristischer Personenanzeiger des transitiven Verbs, 3. Person.',CP)
pron(21,'1sg','= tta/t',['tta','t']); pron(21,'2sg','= mma/m',['mma','m'])

# Modal overview and the prose of the listed modal sections.
v(23,'jussive','-i-','i','Anzeiger des Jussivs (Anm. 79).',page=87,note='Die Übersicht nennt keine vollständige eigene Personentabelle; transitive und intransitive Jussive folgen demselben Bildungsschema.')
for m,f,s,fn,slot,p in [('jussive','-i-','i','Kennzeichen des Jussivs; fehlt bei Stämmen auf l, r und t.',ST,88),('voluntative','-le','le','Voluntativ-Morphem; weitere Segmentierung unklar.',CP,88),('voluntative','l+e','le','Personenkennzeichen des Voluntativs.',CP,88),('imperative','-i','i','Imperativ, 2. Pers. Sg.',CP,88),('imperative','-e','e','Positionsbedingtes Allophon von -i im Imperativ.',CP,88),('imperative','-a','a','Positionsbedingtes Allophon von -i im Imperativ.',CP,88),('jussive_3','-en','en','Personenanzeiger des Jussivs.',CP,91),('jussive_3','-e','e','Verkürzung von -en vor konsonantisch anlautenden Wörtern.',CP,91),('verb_plural_t','-it-','it','Pluralmorphem; t wird als Allomorph betrachtet.',CP,'89-90'),('verb_plural_t','[-id-]','id','Pluralmorphem; gedruckte Lautvariante von -it-.',CP,89),('imperative_pl','-eš','eš','Pluralischer Imperativ.',CP,91),('imperative_pl','-e+š','eš','Pluralischer Imperativ.',CP,91),('jussive_3_o','-o','o','Weiterer Imperativformant; Verweis auf S. 116.',CP,91),('jussive_3_os','-o=š','oš','Weiterer Imperativausgang; Verweis auf S. 116.',CP,91)]: v(24,m,f,s,fn,slot,page=p)
pron(24,'1sg','-tta','tta',90); pron(24,'2pl','-ffa','ffa',90); pron(24,'3sg','-nna','nna',91)
v(24,'old_wish_in','-in','in','Ausgang der Wunschformen der Til-atal-Inschrift; noch nicht völlig geklärt (Anm. 81).',page=90)
v(24,'jussive_3_full','-ien','ien','Ausgang einer Jussivform mit direktem Objekt; Segmentierung von -en diskutiert.',CP,page=89)
for m,f,s,fn,slot,p in [('negative_trans','-u(w)/wa-',['u','uw','wa'],'Negationsformant; im Jussiv in voller Gestalt -wa.',ST,92),('negative_trans','-wa-','wa','Negation in den nicht-indikativischen Modi.',ST,92),('negative_trans','-wa','wa','Volle Gestalt des Negationsformanten.',ST,92),('jussive','-i-','i','Kennzeichen des Jussivs vor -wa-.',ST,92),('voluntative','-lli','lli','Allomorph für die 1. Pers. Sg. des Jussivs (Voluntativ).',CP,92),('jussive_3_negative','-iwaen','iwaen','Ausgang des negierten Jussivs.',CP,92),('owen_modal','-o/uw(a)en',['owaen','owen','uwaen','uwen'],'Von einigen Forschern als negierter Jussiv betrachtet; Deutung offen.',CP,92),('owen_modal','-o/uwen',['owen','uwen'],'Mögliche alternative Lesung; positive Bedeutung erwogen.',CP,92),('owen_modal','-owen','owen','Möglicherweise eigene positive Form.',CP,93)]: v(25,m,f,s,fn,slot,page=p,note='Die Alternative wird nicht entschieden.' if m=='owen_modal' else '')
for m,f,s,fn,p in [('conditional_opt','-ewa','ewa','Formant des konditionellen Optativs; Können oder Wollen.',93),('conditional_opt','/eva/','eva','Lautung des Formanten des konditionellen Optativs.',93),('conditional_opt','-eva','eva','Formant des konditionellen Optativs.',93),('modal_il','-il-','il','Vielleicht zweiter Formant des konditionellen Optativs.',93),('modal_ol','-ol-','ol','Formant vor -eva; sehr ähnliche Funktion wie -il-.',93),('modal_il','/l/','l','Allomorph von -il- bei Zusammentreffen mit Liquid l.',94),('modal_il','/r/','r','Allomorph von -il- bei Zusammentreffen mit Liquid r.',94)]: v(26,m,f,s,fn,page=p)
for f,s in [('-š','š'),('-ša','ša'),('-š(a)',['š','ša'])]: v(26,'verb_plural',f,s,'Pluralanzeiger des Subjekts; -ša vor weiteren Formanten.',CP,page=93 if f!='-š(a)' else 94)
for m,f,s,fn,p in [('debitive_final','-ae/-ai',['ae','ai'],'Debitiv-Finalis; Zweck oder Sollen.',94),('modal_il','-il-','il','Zweiter Formant des Optativs in Kombination mit -ae/-ai.',95),('gerund_im','-i-m-','im','Weitere Formanten bei -ai; i mit nominalisierender Wirkung.',95),('gerund_il','-i-l-','il','Weitere Formanten bei -ai; i mit nominalisierender Wirkung.',95),('nominalizing_i','-i-','i','Nominalisierende Wirkung vor ursprünglich kasueller Endung.',95),('gerund_il_ai','-i-l-ai','ilai','Grammatikalisierte infinite Verbalform; gerundiumähnliche Bildung.','95-96'),('gerund_im_ai','-i-m-ai','imai','Grammatikalisierte infinite Verbalform; gerundiumähnliche Bildung.','95-96')]: v(27,m,f,s,fn,page=p)
v(27,'verb_plural','-š(a)',['š','ša'],'Pluralanzeiger des Handlungssubjekts.',CP,page=95)
v(27,'modal_il','(i)l',['l','il'],'Formant vor ae/ai; fakultatives i in den gedruckten Segmentierungen.',page=95)
pron(27,'3sg','n(na)',['n','nna'],95,note='Gedruckte Segmentierung der Beispiele zu -ae/-ai.')

# Other desiderative forms: preserve whole printed endings where internal analysis remains open.
for m,f,s in [('wish_iles','=i+l=e=š','ileš'),('wish_ilanni','=i+l=anni','ilanni'),('wish_oles','=o+l=e=š','oleš'),('wish_olaes','=o+l=ae=š','olaeš'),('wish_oles','-ol-e-š','oleš'),('wish_olaes','-ol-ae-š','olaeš')]: v(28,m,f,s,'Wunschform; Einzelheiten bedürfen weiterer Klärung.',page=96)
v(28,'wish_ae','-ae-(š)',['ae','aeš'],'Ausgang der Wunschformen; von -ai „Gerundium“ zu trennen.',page=96)
v(28,'modal_il','=il=','il','Modalformant; bevorzugte Deutung gegenüber weiterer Zerlegung.',page=96)
v(28,'modal_ol','=ol=','ol','Modalformant; bevorzugte Deutung gegenüber weiterer Zerlegung.',page=96)
v(28,'desiderative','=anni','anni','Suffix des Desiderativs; intensiv-desiderative Modalform.',page='96-97',note='Als Deutung anderer Autoren referiert; Segmentierung nicht gesichert.')
v(28,'desid_l','-l-','l','Verstärkendes Modalelement nach der referierten Analyse.',page=96,note='Nicht als gesicherte weitere Zerlegung von -il- behandelt.')
v(28,'transitive','-i-','i','In der referierten Analyse vermutetes Transitivkennzeichen.',page=96,note='Die Verfasserin bevorzugt für i+l und o+l jeweils einen Formanten ohne Transitivkennzeichen.')
v(29,'infinitive','-umme','umme','Bildet Nomina der Handlung bzw. Infinitive.')
v(29,'infinitive','-umma','umma','Bildet Nomina der Handlung bzw. Infinitive; produktiv in Nuzi-Fügungen.')

# Modal lists of the bilingue: reproduce the strings printed in the paradigm columns.
for m,f,s,fn,slot in [('voluntative_full','=i= l+e','ile','Voluntativ, 1. Sg.',CP),('imperative','=i/e',['i','e'],'Imperativ, 2. Sg.',CP),('imperative_pl','=e+ š','eš','Imperativ Plural.',CP),('jussive_3_full','=i= en','ien','3. Person des Jussivs.',CP),('jussive_3_o','=u [o]',['u','o'],'3. Person; modale Form.',CP),('jussive_3_os','=u [o]=š',['uš','oš'],'3. Person, auch Plural; modale Form.',CP),('jussive_3pl_full','=i= (i)d en',['iden','iiden'],'Plural des Jussivs.',CP),('desid_sg_full','=i+l= anni','ilanni','Intensiv-desiderative transitive Modalform, Singular.',CP),('desid_pl_full','=i= (i)d= anni',['idanni','iidanni'],'Intensiv-desiderative transitive Modalform, Plural.',CP),('modal_il','(=il=)','il','Fakultativer Formant vor eva.',ST),('modal_il','=il=','il','Formant vor eva im Plural.',ST),('conditional_opt','eva','eva','Formen auf -eva; gelegentlich dem Futur ähnliche Geltung.',ST),('conditional_opt_pl','eva = š','evaš','Plural der Formen auf -eva.',CP),('gerund_il','=i+l','il','Formanten vor =ai; nominalisierendes i.',ST),('gerund_im','=i+m','im','Formanten vor =ai; nominalisierendes i.',ST),('debitive_final','=ai','ai','Formant; ursprünglich eine Kasusendung, davor nominalisierender Themavokal.',ST)]: v(19,m,f,s,fn,slot,page=116)
v(19,'modal_ulil','-u/ol+il',['ulil','olil'],'Formen auf -u/ol+il; intransitiv, auch reflexivisch bzw. distributiv-iterativ gedeutet.',page=117)
v(19,'modal_ulil_i','u/oll = i',['ulli','olli'],'Ausgang der Formen auf -u/ol+il; verbleibendes i nicht recht klar.',page=117)
v(19,'reflex_ul','-ul-','ul','Intransitives, auch reflexivisch verwendetes Suffix (referierte Deutung).',page=117)
v(19,'modal_il','-il-','il','Als Aktionsartsuffix mit distributiv-iterativem Charakter interpretiert.',page=117)
v(19,'unclear_final_i','-i','i','Verbleibender Formant nicht recht klar.',page=117)

# Postpositions are free hosts; only their expressly identified bound elements enter.
add(30,'poss_3sg',P,PR,'-i-','i','Possessiv-Suffix der 3. Pers. Sg. in postpositionalen Ausdrücken.',97)
add(30,'dat',N,CP,'-va','va','Dativ-Kennzeichen des herrschenden Nomens.',98)
add(30,'article_sg',N,GN,'-ne','ne','Morphem -ne am Adjektiv ohne Direktiv- oder Dativmorphem.',98)
for u in [30,31]:
    pron(u,'3pl','/lle/','lle',99,note='Optionales Allomorph von /lla/ ausschließlich nach satzeinleitenden Konjunktionen und der Relativpartikel.')
    pron(u,'3pl','/lla/','lla',99)
    pron(u,'3sg','/me/','me',99,note='Optionales Allomorph von /nna/ ausschließlich nach satzeinleitenden Konjunktionen und der Relativpartikel.')
    pron(u,'3sg','/nna/','nna',99)
for u in [30,32]:
    for f,s,m in [('-an','an','an'),('-nin','nin','nin'),('-ma','ma','ma'),('-man','man','man'),('-mmaman','mmaman','mmaman')]: particle(u,f,s,m,page=100)

def finish():
    for i, sources in attestations.items():
        extra='Weitere Belege derselben Schreibung: '+'; '.join(s['unit']+' (S. '+s['page']+')' for s in sources)+'.'
        entries[i]['notes']=(entries[i].get('notes','')+' '+extra).strip()
    inv={'arm':'hurrian','grammar':{'citation':'Ilse Wegner, Einführung in die hurritische Sprache. Wiesbaden: Harrassowitz Verlag, 2000.','file_sha256':'0'*64},
         'builder':{'model':'runner','session_started_utc':'1970-01-01T00:00:00Z','transcript_file':'runner'},
         'class_order':{'prefix':['p_clitic','p_preposition','p_article','p_person','p_stem'],
                        'suffix':['s_stem','s_gender_number','s_case_person','s_mood','s_pronoun','s_enclitic'],
                        'basis':[
                            {'statement':'Tabelle 1 und Tabelle 2 ordnen Artikel, Possessiv-Pronomen, Pluralisator, Kasus, Suffixaufnahme, Pluralität und Kasus des Bezugswortes, enklitische Pronomina, syntaktische Partikeln an. Diese Reihenfolge ist mit den einmalig verwendbaren Schema-Slots nicht vollständig darstellbar: s_pronoun und s_gender_number müssten wiederholt werden. Deshalb bleibt die Vorlagenreihenfolge als technische Projektion erhalten; sie behauptet keine vollständige hurritische Suffixkette. Siehe notes.md.', 'section':'II.C.2, Tabelle 1 und Tabelle 2', 'page':'65, 69'},
                            {'statement':'Die verbalen Tabellen stellen Wurzelerweiterungen, Tempus und Transitivitäts-/Negationskennzeichen vor Subjektanzeiger, danach Pluralität, enklitische Pronomina und syntaktische Partikeln. Tabelle 8 bis 11 stellen die Modalformanten vor Personen- bzw. Pluralanzeiger; diese wurzelnahen Modalformanten stehen daher in s_stem, finite Personen-/Numerusendungen in s_case_person.', 'section':'II.C.4, Tabelle 3–11', 'page':'80, 82, 85–86, 88, 92–95'}]},
         'entries':entries,'units_read':labels,'units_without_entries':[]}
    (ROOT/'inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
    report='\n'.join(f'| {labels[u]} | {rows[u][4]} | {len(coverage[u])} |' for u in range(len(rows)))
    (ROOT/'work/coverage.md').write_text(report+'\n')
    print(f'{len(entries)} entries; {len(set(e["morpheme_id"] for e in entries))} morpheme IDs; {len(coverage)}/{len(rows)} units with entries.')

if __name__=='__main__': finish()
