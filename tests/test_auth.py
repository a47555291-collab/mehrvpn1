from panel.auth import hash_password,verify_password
def test_password():
 h=hash_password('correct horse battery staple');assert verify_password(h,'correct horse battery staple');assert not verify_password(h,'wrong')
