import pymorphy2

morph = pymorphy2.MorphAnalyzer()


parse = morph.parse("данные")[0]
try:
    main_form = parse.inflect({'nomn'}).text
except AttributeError:
    main_form = parse.normal_form

    res_texts = set()
    for form in parse.inflect({'nomn'}).lexeme:
        res_texts.add(form.word)
    print(*res_texts, sep='\n')