drop table if exists PASTE;
create table PASTE (
	id string not null primary key,
	title string,
	expiration timestamp,
	content string not null,
	password string
);