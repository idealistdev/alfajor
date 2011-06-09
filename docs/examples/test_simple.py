from docs.examples import browser, browser_test


@browser_test()
def test_entering_name():
    browser.open('/')
    assert 'Alfajor' in browser.document['#mainTitle'].text_content
    browser.document['form input[name="name"]'][0].value = 'Juan'
    browser.document['button'][0].click()
    assert 'Juan' in browser.document['h1'][0].text_content
