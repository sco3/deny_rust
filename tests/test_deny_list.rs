mod test_py_deny_list;

use deny_rust::deny_list::DenyList;
use deny_rust::deny_list_rs::DenyListRs;

use deny_rust::build_error::build_error;
use deny_rust::module::deny_rust as dr;
use pyo3::PyResult;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rmpv::Value;
use rmpv::encode::write_value;

const DENY_WORDS: &[&str] = &[
    "abracadabra",
    "hocuspocus",
    "eureka",
    "jumbo",
    "voodoo",
    "juju",
    "mojo",
    "nirvana",
    "chakra",
    "voila",
];
const BLOCK_PROMPT: &str = "The morning sun rose over the distant mountains casting golden rays across the peaceful valley below. Birds sang their melodious songs from the branches of ancient oak trees that had witnessed countless seasons pass. A gentle breeze carried the sweet fragrance of wildflowers that bloomed in vibrant colors throughout the meadow. The river flowed steadily through the landscape creating a soothing rhythm that calmed the mind and spirit. Travelers walked along the winding path sharing stories of their journeys and adventures in faraway lands. The village marketplace bustled with activity as merchants displayed their finest goods and craftspeople demonstrated their skills. Children played games in the town square while elders sat on wooden benches exchanging wisdom and memories from years gone by. The baker prepared fresh loaves of bread filling the air with an irresistible aroma that drew hungry customers to his shop. Farmers brought their harvest from the fields offering fresh vegetables and fruits that reflected the bounty of the season. The blacksmith hammered metal into useful tools and decorative items that would serve the community for years to come. Musicians gathered in the evening to play traditional tunes that had been passed down through generations. Dancers moved gracefully to the rhythms creating patterns that told stories without words. The library housed countless volumes of knowledge collected over centuries providing resources for scholars and curious minds alike. Teachers guided students through lessons helping them discover new ideas and develop their talents. Artists painted landscapes and portraits capturing the beauty of nature and the essence of human expression. The town hall served as a gathering place where citizens discussed important matters and made decisions that affected everyone. Festivals celebrated the changing seasons bringing people together in joyful celebration and shared gratitude. The night sky revealed countless stars that sparkled like diamonds against the dark canvas above. Astronomers studied the celestial bodies seeking to understand the mysteries of the universe and our place within it. Philosophers pondered questions about existence meaning and the nature of reality itself. Historians recorded events ensuring that future generations would learn from the past and build upon the foundations laid by their ancestors. The community thrived through cooperation mutual respect and a shared commitment to creating a better world for all who called this place home. voila.";
const OK_PROMPT: &str = "The morning sun rose over the distant mountains casting golden rays across the peaceful valley below. Birds sang their melodious songs from the branches of ancient oak trees that had witnessed countless seasons pass. A gentle breeze carried the sweet fragrance of wildflowers that bloomed in vibrant colors throughout the meadow. The river flowed steadily through the landscape creating a soothing rhythm that calmed the mind and spirit. Travelers walked along the winding path sharing stories of their journeys and adventures in faraway lands. The village marketplace bustled with activity as merchants displayed their finest goods and craftspeople demonstrated their skills. Children played games in the town square while elders sat on wooden benches exchanging wisdom and memories from years gone by. The baker prepared fresh loaves of bread filling the air with an irresistible aroma that drew hungry customers to his shop. Farmers brought their harvest from the fields offering fresh vegetables and fruits that reflected the bounty of the season. The blacksmith hammered metal into useful tools and decorative items that would serve the community for years to come. Musicians gathered in the evening to play traditional tunes that had been passed down through generations. Dancers moved gracefully to the rhythms creating patterns that told stories without words. The library housed countless volumes of knowledge collected over centuries providing resources for scholars and curious minds alike. Teachers guided students through lessons helping them discover new ideas and develop their talents. Artists painted landscapes and portraits capturing the beauty of nature and the essence of human expression. The town hall served as a gathering place where citizens discussed important matters and made decisions that affected everyone. Festivals celebrated the changing seasons bringing people together in joyful celebration and shared gratitude. The night sky revealed countless stars that sparkled like diamonds against the dark canvas above. Astronomers studied the celestial bodies seeking to understand the mysteries of the universe and our place within it. Philosophers pondered questions about existence meaning and the nature of reality itself. Historians recorded events ensuring that future generations would learn from the past and build upon the foundations laid by their ancestors. The community thrived through cooperation mutual respect and a shared commitment to creating a better world for all who called this place home.";

fn common_test_logic<T: deny_rust::matcher::Matcher>(deny_list: &T, py: Python) {
    assert!(deny_list.is_match("111 voila  222"));
    assert!(deny_list.is_match("111 chakra 222 voila"));
    assert!(!deny_list.is_match("111 222"));

    check_bad_msgpack(deny_list);

    check_msgpack_ok(deny_list);
    check_msgpack_blocked(deny_list);

    // test blocked prompts

    assert!(deny_list.is_match(BLOCK_PROMPT));

    let list_data: Vec<String> = BLOCK_PROMPT.split(' ').map(ToString::to_string).collect();
    let list = PyList::new(py, list_data).unwrap();
    assert!(deny_list.scan_any(&list));

    let dict = PyDict::new(py);
    dict.set_item("user", BLOCK_PROMPT).unwrap();
    // should not scan non-string, improves test coverage
    dict.set_item("id", 1).unwrap();

    assert!(deny_list.scan(&dict));
    assert!(deny_list.scan_any(&dict));

    // test non blocked prompts
    assert!(!deny_list.is_match(OK_PROMPT));

    dict.clear();
    dict.set_item("user", OK_PROMPT).unwrap();
    // should not scan non-string, improves test coverage
    dict.set_item("id", 1).unwrap();
    assert!(!deny_list.scan(&dict));
    assert!(!deny_list.scan_any(&dict));

    let list_data: Vec<String> = OK_PROMPT.split(' ').map(ToString::to_string).collect();
    let list = PyList::new(py, &list_data).unwrap();

    assert!(!deny_list.scan_any(&list));
}

fn check_bad_msgpack<T: deny_rust::matcher::Matcher>(deny_list: &T) {
    // Empty buffer - caught by safety check at line 61-63
    let buf: &[u8] = &[];
    assert!(!deny_list.scan_msgpack(buf));

    // Truncated MessagePack: FixArray claiming 2 elements but only 1 byte of data
    // 0x92 = fixarray(2), followed by incomplete data
    // This triggers line 67 when recursive traversal tries to read beyond buffer
    let buf: &[u8] = &[0x92, 0x01]; // array of 2, but only 1 element present
    assert!(!deny_list.scan_msgpack(buf));
}
fn check_msgpack_ok<T: deny_rust::matcher::Matcher>(deny_list: &T) {
    let map = Value::Map(vec![
        (Value::from("id"), Value::from("ok")),
        (Value::from("user"), Value::from(OK_PROMPT)),
    ]);
    let mut buf = Vec::new();
    write_value(&mut buf, &map).unwrap();

    assert!(!deny_list.scan_msgpack(buf.as_slice()));
}
fn check_msgpack_blocked<T: deny_rust::matcher::Matcher>(deny_list: &T) {
    let map = Value::Map(vec![
        (Value::from("id"), Value::from("block")),
        (Value::from("user"), Value::from(BLOCK_PROMPT)),
    ]);
    let mut buf = Vec::new();
    write_value(&mut buf, &map).unwrap();

    assert!(deny_list.scan_msgpack(buf.as_slice()));
}

#[test]
fn test_deny_lists() -> PyResult<()> {
    let words: Vec<String> = DENY_WORDS.iter().map(ToString::to_string).collect();
    let deny_list = DenyList::new(words.clone())?;
    let deny_list_rs = DenyListRs::new(words.clone())?;

    Python::initialize();
    Python::attach(|py| {
        common_test_logic(&deny_list, py);
        common_test_logic(&deny_list_rs, py);

        // test py module
        let module = PyModule::new(py, "modules").unwrap();
        dr(&module).unwrap();
    });

    let dummy_error = "mock error";
    let py_err = build_error(dummy_error);
    assert!(py_err.to_string().contains("mock error"));

    Ok(())
}
