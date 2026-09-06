from panel.security import valid_name
def test_names():
 assert valid_name('alice-01') and valid_name('a_b.c')
 assert not valid_name('../x') and not valid_name('a/b')
