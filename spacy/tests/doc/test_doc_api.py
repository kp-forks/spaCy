import pytest
import numpy
from spacy.tokens import Doc, Span
from spacy.vocab import Vocab
from spacy.lexeme import Lexeme
from spacy.lang.en import English
from spacy.attrs import ENT_TYPE, ENT_IOB, SENT_START, HEAD, DEP, MORPH

from ..util import get_doc


def test_doc_api_init(en_vocab):
    # set sent_start by sent_starts
    doc = Doc(
        en_vocab, words=["a", "b", "c", "d"], sent_starts=[True, False, True, False]
    )
    assert [t.is_sent_start for t in doc] == [True, False, True, False]

    # set sent_start by heads
    doc = Doc(
        en_vocab, words=["a", "b", "c", "d"], heads=[0, 0, 2, 2], deps=["dep"] * 4
    )
    assert [t.is_sent_start for t in doc] == [True, False, True, False]

    # heads override sent_starts
    doc = Doc(
        en_vocab, words=["a", "b", "c", "d"], sent_starts=[True] * 4, heads=[0, 0, 2, 2], deps=["dep"] * 4
    )
    assert [t.is_sent_start for t in doc] == [True, False, True, False]


@pytest.mark.parametrize("text", [["one", "two", "three"]])
def test_doc_api_compare_by_string_position(en_vocab, text):
    doc = Doc(en_vocab, words=text)
    # Get the tokens in this order, so their ID ordering doesn't match the idx
    token3 = doc[-1]
    token2 = doc[-2]
    token1 = doc[-1]
    token1, token2, token3 = doc
    assert token1 < token2 < token3
    assert not token1 > token2
    assert token2 > token1
    assert token2 <= token3
    assert token3 >= token1


def test_doc_api_getitem(en_tokenizer):
    text = "Give it back! He pleaded."
    tokens = en_tokenizer(text)
    assert tokens[0].text == "Give"
    assert tokens[-1].text == "."
    with pytest.raises(IndexError):
        tokens[len(tokens)]

    def to_str(span):
        return "/".join(token.text for token in span)

    span = tokens[1:1]
    assert not to_str(span)
    span = tokens[1:4]
    assert to_str(span) == "it/back/!"
    span = tokens[1:4:1]
    assert to_str(span) == "it/back/!"
    with pytest.raises(ValueError):
        tokens[1:4:2]
    with pytest.raises(ValueError):
        tokens[1:4:-1]

    span = tokens[-3:6]
    assert to_str(span) == "He/pleaded"
    span = tokens[4:-1]
    assert to_str(span) == "He/pleaded"
    span = tokens[-5:-3]
    assert to_str(span) == "back/!"
    span = tokens[5:4]
    assert span.start == span.end == 5 and not to_str(span)
    span = tokens[4:-3]
    assert span.start == span.end == 4 and not to_str(span)

    span = tokens[:]
    assert to_str(span) == "Give/it/back/!/He/pleaded/."
    span = tokens[4:]
    assert to_str(span) == "He/pleaded/."
    span = tokens[:4]
    assert to_str(span) == "Give/it/back/!"
    span = tokens[:-3]
    assert to_str(span) == "Give/it/back/!"
    span = tokens[-3:]
    assert to_str(span) == "He/pleaded/."

    span = tokens[4:50]
    assert to_str(span) == "He/pleaded/."
    span = tokens[-50:4]
    assert to_str(span) == "Give/it/back/!"
    span = tokens[-50:-40]
    assert span.start == span.end == 0 and not to_str(span)
    span = tokens[40:50]
    assert span.start == span.end == 7 and not to_str(span)

    span = tokens[1:4]
    assert span[0].orth_ == "it"
    subspan = span[:]
    assert to_str(subspan) == "it/back/!"
    subspan = span[:2]
    assert to_str(subspan) == "it/back"
    subspan = span[1:]
    assert to_str(subspan) == "back/!"
    subspan = span[:-1]
    assert to_str(subspan) == "it/back"
    subspan = span[-2:]
    assert to_str(subspan) == "back/!"
    subspan = span[1:2]
    assert to_str(subspan) == "back"
    subspan = span[-2:-1]
    assert to_str(subspan) == "back"
    subspan = span[-50:50]
    assert to_str(subspan) == "it/back/!"
    subspan = span[50:-50]
    assert subspan.start == subspan.end == 4 and not to_str(subspan)


@pytest.mark.parametrize(
    "text", ["Give it back! He pleaded.", " Give it back! He pleaded. "]
)
def test_doc_api_serialize(en_tokenizer, text):
    tokens = en_tokenizer(text)
    tokens[0].lemma_ = "lemma"
    tokens[0].norm_ = "norm"
    tokens.ents = [(tokens.vocab.strings["PRODUCT"], 0, 1)]
    tokens[0].ent_kb_id_ = "ent_kb_id"
    new_tokens = Doc(tokens.vocab).from_bytes(tokens.to_bytes())
    assert tokens.text == new_tokens.text
    assert [t.text for t in tokens] == [t.text for t in new_tokens]
    assert [t.orth for t in tokens] == [t.orth for t in new_tokens]
    assert new_tokens[0].lemma_ == "lemma"
    assert new_tokens[0].norm_ == "norm"
    assert new_tokens[0].ent_kb_id_ == "ent_kb_id"

    new_tokens = Doc(tokens.vocab).from_bytes(
        tokens.to_bytes(exclude=["tensor"]), exclude=["tensor"]
    )
    assert tokens.text == new_tokens.text
    assert [t.text for t in tokens] == [t.text for t in new_tokens]
    assert [t.orth for t in tokens] == [t.orth for t in new_tokens]

    new_tokens = Doc(tokens.vocab).from_bytes(
        tokens.to_bytes(exclude=["sentiment"]), exclude=["sentiment"]
    )
    assert tokens.text == new_tokens.text
    assert [t.text for t in tokens] == [t.text for t in new_tokens]
    assert [t.orth for t in tokens] == [t.orth for t in new_tokens]


def test_doc_api_set_ents(en_tokenizer):
    text = "I use goggle chrone to surf the web"
    tokens = en_tokenizer(text)
    assert len(tokens.ents) == 0
    tokens.ents = [(tokens.vocab.strings["PRODUCT"], 2, 4)]
    assert len(list(tokens.ents)) == 1
    assert [t.ent_iob for t in tokens] == [0, 0, 3, 1, 0, 0, 0, 0]
    assert tokens.ents[0].label_ == "PRODUCT"
    assert tokens.ents[0].start == 2
    assert tokens.ents[0].end == 4


def test_doc_api_sents_empty_string(en_tokenizer):
    doc = en_tokenizer("")
    sents = list(doc.sents)
    assert len(sents) == 0


def test_doc_api_runtime_error(en_tokenizer):
    # Example that caused run-time error while parsing Reddit
    # fmt: off
    text = "67% of black households are single parent \n\n72% of all black babies born out of wedlock \n\n50% of all black kids don\u2019t finish high school"
    deps = ["nummod", "nsubj", "prep", "amod", "pobj", "ROOT", "amod", "attr", "", "nummod", "appos", "prep", "det",
            "amod", "pobj", "acl", "prep", "prep", "pobj",
            "", "nummod", "nsubj", "prep", "det", "amod", "pobj", "aux", "neg", "ccomp", "amod", "dobj"]
    # fmt: on
    tokens = en_tokenizer(text)
    doc = get_doc(tokens.vocab, words=[t.text for t in tokens], deps=deps)
    nps = []
    for np in doc.noun_chunks:
        while len(np) > 1 and np[0].dep_ not in ("advmod", "amod", "compound"):
            np = np[1:]
        if len(np) > 1:
            nps.append(np)
    with doc.retokenize() as retokenizer:
        for np in nps:
            attrs = {
                "tag": np.root.tag_,
                "lemma": np.text,
                "ent_type": np.root.ent_type_,
            }
            retokenizer.merge(np, attrs=attrs)


def test_doc_api_right_edge(en_tokenizer):
    """Test for bug occurring from Unshift action, causing incorrect right edge"""
    # fmt: off
    text = "I have proposed to myself, for the sake of such as live under the government of the Romans, to translate those books into the Greek tongue."
    heads = [2, 1, 0, -1, -1, -3, 15, 1, -2, -1, 1, -3, -1, -1, 1, -2, -1, 1,
             -2, -7, 1, -19, 1, -2, -3, 2, 1, -3, -26]
    deps = ["dep"] * len(heads)
    # fmt: on

    tokens = en_tokenizer(text)
    doc = get_doc(tokens.vocab, words=[t.text for t in tokens], heads=heads, deps=deps)
    assert doc[6].text == "for"
    subtree = [w.text for w in doc[6].subtree]
    # fmt: off
    assert subtree == ["for", "the", "sake", "of", "such", "as", "live", "under", "the", "government", "of", "the", "Romans", ","]
    # fmt: on
    assert doc[6].right_edge.text == ","


def test_doc_api_has_vector():
    vocab = Vocab()
    vocab.reset_vectors(width=2)
    vocab.set_vector("kitten", vector=numpy.asarray([0.0, 2.0], dtype="f"))
    doc = Doc(vocab, words=["kitten"])
    assert doc.has_vector


def test_doc_api_similarity_match():
    doc = Doc(Vocab(), words=["a"])
    assert doc.similarity(doc[0]) == 1.0
    assert doc.similarity(doc.vocab["a"]) == 1.0
    doc2 = Doc(doc.vocab, words=["a", "b", "c"])
    with pytest.warns(UserWarning):
        assert doc.similarity(doc2[:1]) == 1.0
        assert doc.similarity(doc2) == 0.0


@pytest.mark.parametrize(
    "sentence,heads,lca_matrix",
    [
        (
            "the lazy dog slept",
            [2, 1, 1, 0],
            numpy.array([[0, 2, 2, 3], [2, 1, 2, 3], [2, 2, 2, 3], [3, 3, 3, 3]]),
        ),
        (
            "The lazy dog slept. The quick fox jumped",
            [2, 1, 1, 0, -1, 2, 1, 1, 0],
            numpy.array(
                [
                    [0, 2, 2, 3, 3, -1, -1, -1, -1],
                    [2, 1, 2, 3, 3, -1, -1, -1, -1],
                    [2, 2, 2, 3, 3, -1, -1, -1, -1],
                    [3, 3, 3, 3, 3, -1, -1, -1, -1],
                    [3, 3, 3, 3, 4, -1, -1, -1, -1],
                    [-1, -1, -1, -1, -1, 5, 7, 7, 8],
                    [-1, -1, -1, -1, -1, 7, 6, 7, 8],
                    [-1, -1, -1, -1, -1, 7, 7, 7, 8],
                    [-1, -1, -1, -1, -1, 8, 8, 8, 8],
                ]
            ),
        ),
    ],
)
def test_lowest_common_ancestor(en_tokenizer, sentence, heads, lca_matrix):
    tokens = en_tokenizer(sentence)
    doc = get_doc(
        tokens.vocab, [t.text for t in tokens], heads=heads, deps=["dep"] * len(heads)
    )
    lca = doc.get_lca_matrix()
    assert (lca == lca_matrix).all()
    assert lca[1, 1] == 1
    assert lca[0, 1] == 2
    assert lca[1, 2] == 2


def test_doc_is_nered(en_vocab):
    words = ["I", "live", "in", "New", "York"]
    doc = Doc(en_vocab, words=words)
    assert not doc.has_annotation("ENT_IOB")
    doc.ents = [Span(doc, 3, 5, label="GPE")]
    assert doc.has_annotation("ENT_IOB")
    # Test creating doc from array with unknown values
    arr = numpy.array([[0, 0], [0, 0], [0, 0], [384, 3], [384, 1]], dtype="uint64")
    doc = Doc(en_vocab, words=words).from_array([ENT_TYPE, ENT_IOB], arr)
    assert doc.has_annotation("ENT_IOB")
    # Test serialization
    new_doc = Doc(en_vocab).from_bytes(doc.to_bytes())
    assert new_doc.has_annotation("ENT_IOB")


def test_doc_from_array_sent_starts(en_vocab):
    words = ["I", "live", "in", "New", "York", ".", "I", "like", "cats", "."]
    heads = [0, -1, -2, -3, -4, -5, 0, -1, -2, -3]
    # fmt: off
    deps = ["ROOT", "dep", "dep", "dep", "dep", "dep", "ROOT", "dep", "dep", "dep"]
    # fmt: on
    doc = get_doc(en_vocab, words=words, heads=heads, deps=deps)

    # HEAD overrides SENT_START without warning
    attrs = [SENT_START, HEAD]
    arr = doc.to_array(attrs)
    new_doc = Doc(en_vocab, words=words)
    new_doc.from_array(attrs, arr)

    # no warning using default attrs
    attrs = doc._get_array_attrs()
    arr = doc.to_array(attrs)
    with pytest.warns(None) as record:
        new_doc.from_array(attrs, arr)
        assert len(record) == 0

    # only SENT_START uses SENT_START
    attrs = [SENT_START]
    arr = doc.to_array(attrs)
    new_doc = Doc(en_vocab, words=words)
    new_doc.from_array(attrs, arr)
    assert [t.is_sent_start for t in doc] == [t.is_sent_start for t in new_doc]
    assert not new_doc.has_annotation("DEP")

    # only HEAD uses HEAD
    attrs = [HEAD, DEP]
    arr = doc.to_array(attrs)
    new_doc = Doc(en_vocab, words=words)
    new_doc.from_array(attrs, arr)
    assert [t.is_sent_start for t in doc] == [t.is_sent_start for t in new_doc]
    assert new_doc.has_annotation("DEP")


def test_doc_from_array_morph(en_vocab):
    words = ["I", "live", "in", "New", "York", "."]
    # fmt: off
    morphs = ["Feat1=A", "Feat1=B", "Feat1=C", "Feat1=A|Feat2=D", "Feat2=E", "Feat3=F"]
    # fmt: on
    doc = Doc(en_vocab, words=words)
    for i, morph in enumerate(morphs):
        doc[i].morph_ = morph

    attrs = [MORPH]
    arr = doc.to_array(attrs)
    new_doc = Doc(en_vocab, words=words)
    new_doc.from_array(attrs, arr)

    assert [t.morph_ for t in new_doc] == morphs
    assert [t.morph_ for t in doc] == [t.morph_ for t in new_doc]


def test_doc_api_from_docs(en_tokenizer, de_tokenizer):
    en_texts = ["Merging the docs is fun.", "", "They don't think alike."]
    en_texts_without_empty = [t for t in en_texts if len(t)]
    de_text = "Wie war die Frage?"
    en_docs = [en_tokenizer(text) for text in en_texts]
    docs_idx = en_texts[0].index("docs")
    de_doc = de_tokenizer(de_text)
    en_docs[0].user_data[("._.", "is_ambiguous", docs_idx, None)] = (
        True,
        None,
        None,
        None,
    )

    assert Doc.from_docs([]) is None

    assert de_doc is not Doc.from_docs([de_doc])
    assert str(de_doc) == str(Doc.from_docs([de_doc]))

    with pytest.raises(ValueError):
        Doc.from_docs(en_docs + [de_doc])

    m_doc = Doc.from_docs(en_docs)
    assert len(en_texts_without_empty) == len(list(m_doc.sents))
    assert len(str(m_doc)) > len(en_texts[0]) + len(en_texts[1])
    assert str(m_doc) == " ".join(en_texts_without_empty)
    p_token = m_doc[len(en_docs[0]) - 1]
    assert p_token.text == "." and bool(p_token.whitespace_)
    en_docs_tokens = [t for doc in en_docs for t in doc]
    assert len(m_doc) == len(en_docs_tokens)
    think_idx = len(en_texts[0]) + 1 + en_texts[2].index("think")
    assert m_doc[9].idx == think_idx
    with pytest.raises(AttributeError):
        # not callable, because it was not set via set_extension
        m_doc[2]._.is_ambiguous
    assert len(m_doc.user_data) == len(en_docs[0].user_data)  # but it's there

    m_doc = Doc.from_docs(en_docs, ensure_whitespace=False)
    assert len(en_texts_without_empty) == len(list(m_doc.sents))
    assert len(str(m_doc)) == sum(len(t) for t in en_texts)
    assert str(m_doc) == "".join(en_texts)
    p_token = m_doc[len(en_docs[0]) - 1]
    assert p_token.text == "." and not bool(p_token.whitespace_)
    en_docs_tokens = [t for doc in en_docs for t in doc]
    assert len(m_doc) == len(en_docs_tokens)
    think_idx = len(en_texts[0]) + 0 + en_texts[2].index("think")
    assert m_doc[9].idx == think_idx

    m_doc = Doc.from_docs(en_docs, attrs=["lemma", "length", "pos"])
    assert len(str(m_doc)) > len(en_texts[0]) + len(en_texts[1])
    # space delimiter considered, although spacy attribute was missing
    assert str(m_doc) == " ".join(en_texts_without_empty)
    p_token = m_doc[len(en_docs[0]) - 1]
    assert p_token.text == "." and bool(p_token.whitespace_)
    en_docs_tokens = [t for doc in en_docs for t in doc]
    assert len(m_doc) == len(en_docs_tokens)
    think_idx = len(en_texts[0]) + 1 + en_texts[2].index("think")
    assert m_doc[9].idx == think_idx


def test_doc_api_from_docs_ents(en_tokenizer):
    texts = ["Merging the docs is fun.", "They don't think alike."]
    docs = [en_tokenizer(t) for t in texts]
    docs[0].ents = ()
    docs[1].ents = (Span(docs[1], 0, 1, label="foo"),)
    doc = Doc.from_docs(docs)
    assert len(doc.ents) == 1


def test_doc_lang(en_vocab):
    doc = Doc(en_vocab, words=["Hello", "world"])
    assert doc.lang_ == "en"
    assert doc.lang == en_vocab.strings["en"]
    assert doc[0].lang_ == "en"
    assert doc[0].lang == en_vocab.strings["en"]
    nlp = English()
    doc = nlp("Hello world")
    assert doc.lang_ == "en"
    assert doc.lang == en_vocab.strings["en"]
    assert doc[0].lang_ == "en"
    assert doc[0].lang == en_vocab.strings["en"]


def test_token_lexeme(en_vocab):
    """Test that tokens expose their lexeme."""
    token = Doc(en_vocab, words=["Hello", "world"])[0]
    assert isinstance(token.lex, Lexeme)
    assert token.lex.text == token.text
    assert en_vocab[token.orth] == token.lex


def test_has_annotation(en_vocab):
    doc = Doc(en_vocab, words=["Hello", "world"])
    attrs = ("TAG", "POS", "MORPH", "LEMMA", "DEP", "HEAD", "ENT_IOB", "ENT_TYPE")
    for attr in attrs:
        assert not doc.has_annotation(attr)

    doc[0].tag_ = "A"
    doc[0].pos_ = "X"
    doc[0].morph_ = "Feat=Val"
    doc[0].lemma_ = "a"
    doc[0].dep_ = "dep"
    doc[0].head = doc[1]
    doc.ents = [Span(doc, 0, 1, label="HELLO")]

    for attr in attrs:
        assert doc.has_annotation(attr)
        assert not doc.has_annotation(attr, require_complete=True)

    doc[1].tag_ = "A"
    doc[1].pos_ = "X"
    doc[1].morph_ = ""
    doc[1].lemma_ = "a"
    doc[1].dep_ = "dep"
    doc.ents = [Span(doc, 0, 2, label="HELLO")]

    for attr in attrs:
        assert doc.has_annotation(attr)
        assert doc.has_annotation(attr, require_complete=True)


def test_is_flags_deprecated(en_tokenizer):
    doc = en_tokenizer("test")
    with pytest.deprecated_call():
        doc.is_tagged
    with pytest.deprecated_call():
        doc.is_parsed
    with pytest.deprecated_call():
        doc.is_nered
    with pytest.deprecated_call():
        doc.is_sentenced
