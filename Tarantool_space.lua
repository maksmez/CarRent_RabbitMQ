box.cfg{listen = 3302}
local function init()
	s = box.schema.space.create('user_token')
	s:format({
			 {name = 'token', type = 'string'},
			 {name = 'id', type = 'integer'},
			 {name = 'ttl', type = 'integer'}
			 })
	s:create_index('primary', {
			 type = 'hash',
			 parts = {'token'}
			 })
 end
 box.once('init', init)