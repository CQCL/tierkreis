use std::{
    fs::{DirEntry, File, read_dir},
    io::Read,
    path::PathBuf,
};

use chrono::{DateTime, Utc};
use color_eyre::Result;
use crossterm::event::{self, Event, KeyCode, KeyEvent};
use directories::UserDirs;
use ratatui::{
    DefaultTerminal, Frame,
    layout::{Constraint, Layout},
    style::Stylize,
    widgets::{Block, Borders, Cell, Paragraph, Row, Table, Wrap},
};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct Metaddata {
    name: String,
}

#[derive(Serialize, Deserialize)]
struct Definition {
    function_name: String,
}

fn main() -> Result<()> {
    color_eyre::install()?;
    let terminal = ratatui::init();

    let user_dirs = UserDirs::new().unwrap();
    let home_dir = user_dirs.home_dir();
    let checkpoints_dir = home_dir.join(".tierkreis").join("checkpoints");

    let mut app = App::new(checkpoints_dir);
    let result = app.run(terminal);
    ratatui::restore();
    result
}

#[derive(Default)]
struct App {
    checkpoints_dir: PathBuf,
    workflow_select_idx: usize,
    selected: bool,
    workflows: Vec<Workflow>,

    logs_buffer: String,
    logs_scroll: u16,

    has_error: bool,
    error_function: String,
    error_buffer: String,
}

struct Workflow {
    id: String,
    name: String,
    modified: DateTime<Utc>,
    dir: DirEntry,
}

impl App {
    pub fn new(checkpoints_dir: PathBuf) -> Self {
        Self {
            checkpoints_dir,
            ..Default::default()
        }
    }

    fn run(&mut self, mut terminal: DefaultTerminal) -> Result<()> {
        loop {
            if !self.selected {
                self.refresh_workflows()?;
            } else {
                self.read_logs()?;
                self.read_errors()?;
            }

            terminal.draw(|frame| self.render(frame))?;
            let event = event::read()?;
            if matches!(
                event,
                Event::Key(KeyEvent {
                    code: KeyCode::Esc,
                    ..
                })
            ) {
                break Ok(());
            }
            if matches!(
                event,
                Event::Key(KeyEvent {
                    code: KeyCode::Down,
                    ..
                })
            ) {
                if self.selected {
                    self.logs_scroll += 1;
                } else {
                    if self.workflow_select_idx < self.workflows.len() - 1 {
                        self.workflow_select_idx += 1;
                    }
                }
            }
            if matches!(
                event,
                Event::Key(KeyEvent {
                    code: KeyCode::Up,
                    ..
                })
            ) {
                if self.selected {
                    if self.logs_scroll > 0 {
                        self.logs_scroll -= 1;
                    }
                } else {
                    if self.workflow_select_idx > 0 {
                        self.workflow_select_idx -= 1;
                    }
                }
            }

            if matches!(
                event,
                Event::Key(KeyEvent {
                    code: KeyCode::Right,
                    ..
                })
            ) {
                self.selected = true;
            }

            if matches!(
                event,
                Event::Key(KeyEvent {
                    code: KeyCode::Left,
                    ..
                })
            ) {
                self.selected = false;
                self.logs_scroll = 0;
            }
        }
    }

    fn refresh_workflows(&mut self) -> Result<()> {
        let mut workflows = Vec::new();

        for workflow_dir in read_dir(&self.checkpoints_dir)? {
            let workflow_dir = workflow_dir?;
            let workflow_file_name = workflow_dir.file_name();
            let workflow_id = workflow_file_name.to_str().unwrap();

            let metadata_file_path = workflow_dir.path().join("_metadata");
            let metadata_file = File::open(metadata_file_path)?;
            let modified = metadata_file.metadata().unwrap().modified()?;
            let metadata: Metaddata = serde_json::from_reader(metadata_file)?;
            let modified = DateTime::<Utc>::from(modified);

            workflows.push(Workflow {
                id: workflow_id.to_string(),
                name: metadata.name,
                modified,
                dir: workflow_dir,
            });
        }

        workflows.sort_by(|x, y| y.modified.cmp(&x.modified));

        self.workflows = workflows;

        Ok(())
    }

    fn read_logs(&mut self) -> Result<()> {
        let workflow = &self.workflows[self.workflow_select_idx];
        let logs_path = workflow.dir.path().join("logs");

        self.logs_buffer.clear();
        let mut log_file = File::open(logs_path)?;
        log_file.read_to_string(&mut self.logs_buffer)?;

        Ok(())
    }

    fn read_errors(&mut self) -> Result<()> {
        let workflow = &self.workflows[self.workflow_select_idx];

        self.has_error = false;
        for error_file_path in glob::glob(&format!(
            "{}/**/_error",
            workflow.dir.path().to_str().unwrap()
        ))? {
            self.has_error = true;
            let error_file_path = error_file_path?;
            // assuming a single error
            self.error_buffer.clear();
            let mut error_file = File::open(&error_file_path)?;
            error_file.read_to_string(&mut self.error_buffer)?;
            // todo: find out what function caused it

            let definition_file_path = error_file_path.parent().unwrap().join("definition");
            let definition_file = File::open(definition_file_path)?;
            let definition: Definition = serde_json::from_reader(definition_file)?;

            self.error_function = definition.function_name;
        }

        Ok(())
    }

    fn render(&self, frame: &mut Frame) {
        if !self.selected {
            self.render_menu(frame);
        } else {
            self.render_workflow(frame);
        }
    }

    fn render_menu(&self, frame: &mut Frame) {
        let mut rows = Vec::new();
        let header = ["Workflow ID", "Name", "Last Updated"]
            .into_iter()
            .map(Cell::from)
            .collect::<Row>()
            .height(1)
            .bold()
            .black()
            .on_white();
        rows.push(header);

        for (idx, workflow) in self.workflows.iter().enumerate() {
            let cells = [
                Cell::new(workflow.id.clone()),
                Cell::new(workflow.name.clone()),
                Cell::new(format!("{:?}", workflow.modified)),
            ];
            let mut row = Row::new(cells);
            if idx == self.workflow_select_idx {
                row = row.blue();
            }
            rows.push(row);
        }
        let table = Table::new(
            rows,
            [
                Constraint::Length(36),
                Constraint::Min(32),
                Constraint::Min(32),
            ],
        );
        frame.render_widget(table, frame.area());
    }

    fn render_workflow(&self, frame: &mut Frame) {
        let workflow = &self.workflows[self.workflow_select_idx];
        let block = Block::new()
            .title(workflow.name.clone())
            .borders(Borders::all());

        let logs = Paragraph::new(self.logs_buffer.clone())
            .wrap(Wrap { trim: true })
            .scroll((self.logs_scroll, 0))
            .block(block);

        if self.has_error {
            let layout =
                Layout::vertical([Constraint::Min(1), Constraint::Max(3)]).split(frame.area());

            frame.render_widget(logs, layout[0]);

            let error_block = Block::new()
                .title(self.error_function.clone())
                .borders(Borders::all())
                .red();

            let error = Paragraph::new(self.error_buffer.clone())
                .wrap(Wrap { trim: true })
                .block(error_block);

            frame.render_widget(error, layout[1]);
        } else {
            frame.render_widget(logs, frame.area());
        }
    }
}
