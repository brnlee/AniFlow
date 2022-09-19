use std::collections::HashMap;
use std::future::Future;
use inquire::error::InquireResult;
use serde_derive::Deserialize;
use serde_derive::Serialize;
use inquire::InquireError;
use inquire::Select;
use reqwest::blocking::Response;
use reqwest::blocking::Client;
use reqwest::Result;

fn main() -> () {
    let http_client = &Client::new();
    let torrents_list = get_torrents_list(http_client);
    let mut eps = Vec::new();
    match torrents_list {
        Ok(tl) => {
            for torrent in tl {
                println!("{}", torrent.name);
                let episodes = get_episodes(http_client, &torrent.hash);
                match episodes {
                    Ok(e) => {
                        for episode in e {
                            // println!("\t{:?}", episode);
                            if episode.progress == 1.0 {
                                let path = format!("{}{}", torrent.save_path, episode.name);
                                eps.push(path)
                                }
                        }
                    }
                    Err(e) => {eprintln!("Couldn't get episodes. {:?}", e)}
                }

            }
        }
        Err(_) => { eprintln!("YIKES. Could not get torrents list.") }
    }

    let ans: InquireResult<String> = Select::new("What do you want to watch?", eps).prompt();

    match ans {
        Ok(path) => {
            match open::that(&path){
                Ok(_) => {println!("Opened {}", path)}
                Err(_) => {eprintln!("Failed to open {}", path)}
            };
        }
        Err(_) => println!("There was an error, please try again"),
    };
}

const QBITTORRENT_API: &str = "http://localhost:8080/api/v2";
const TORRENTS_INFO: &str = "/torrents/info";
const TORRENTS_FILES: &str = "/torrents/files";

fn get_torrents_list(http_client: &Client) -> Result<TorrentList> {
    http_client
        .get(format!("{}{}", QBITTORRENT_API, TORRENTS_INFO))
        .query(&[("category", "Anime"), ("sort", "name")])
        .send()?
        .json::<TorrentList>()
}

fn get_episodes(http_client: &Client, torrent_hash: &str) -> Result<EpisodeFiles> {
    http_client
        .get(format!("{}{}", QBITTORRENT_API, TORRENTS_FILES))
        .query(&[("hash", torrent_hash)])
        .send()?
        .json::<EpisodeFiles>()
}

fn clear_command_line() {
    print!("{}[2J", 27 as char);
}


pub type TorrentList = Vec<Torrent>;

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Torrent {
    pub name: String,
    #[serde(rename = "save_path")]
    pub save_path: String,
    pub hash: String,
}

pub type EpisodeFiles = Vec<EpisodeFile>;

#[derive(Debug, Serialize, Deserialize)]
pub struct EpisodeFile {
    // #[serde(rename = "availability")]
    // availability: i64,

    // #[serde(rename = "is_seed")]
    // is_seed: bool,

    #[serde(rename = "name")]
    name: String,

    // #[serde(rename = "piece_range")]
    // piece_range: Vec<i64>,

    // #[serde(rename = "priority")]
    // priority: i64,

    #[serde(rename = "progress")]
    progress: f32,

    // #[serde(rename = "size")]
    // size: i64,
}
