use std::{
    fs::{DirEntry, File, read_dir},
    io::Read,
    path::PathBuf,
};

use chrono::{DateTime, Utc};
use color_eyre::{Result, Section};
use crossterm::event::{self, Event, KeyCode, KeyEvent};
use directories::UserDirs;
use itertools::Itertools;
use ratatui::{
    DefaultTerminal, Frame,
    layout::{Constraint, Layout, Margin},
    style::{Style, Stylize},
    text::{Line, Span},
    widgets::{
        Block, Borders, Cell, Paragraph, Row, Scrollbar, ScrollbarState, Table, TableState, Wrap,
    },
};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct Metaddata {
    name: Option<String>,
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
    // workflow_select_idx: usize,
    workflow_table_state: TableState,
    selected: bool,
    workflows: Vec<Workflow>,

    logs_buffer: String,
    logs_scroll: usize,
    logs_scroll_state: ScrollbarState,

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
            workflow_table_state: TableState::new().with_selected(Some(1)),
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
                    self.logs_scroll = self.logs_scroll.saturating_add(1);
                    self.logs_scroll_state = self.logs_scroll_state.position(self.logs_scroll);
                } else {
                    self.workflow_table_state.select_next();
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
                    self.logs_scroll = self.logs_scroll.saturating_sub(1);
                    self.logs_scroll_state = self.logs_scroll_state.position(self.logs_scroll);
                } else {
                    if self.workflow_table_state.selected() != Some(1) {
                        self.workflow_table_state.select_previous();
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
                self.logs_scroll_state = self.logs_scroll_state.position(0);
            }
        }
    }

    fn refresh_workflows(&mut self) -> Result<()> {
        let mut workflows = Vec::new();

        for workflow_dir in read_dir(&self.checkpoints_dir)
            .with_note(|| "Checkpoints directory not found.")
            .with_suggestion(
                || "Checkpoint directory may not exist, try running a workflow first.",
            )?
        {
            let workflow_dir = workflow_dir?;
            let workflow_file_name = workflow_dir.file_name();
            let workflow_id = workflow_file_name.to_str().unwrap();

            let metadata_file_path = workflow_dir.path().join("_metadata");
            let metadata_file = File::open(&metadata_file_path)?;
            let modified = metadata_file.metadata().unwrap().modified()?;
            let metadata: Metaddata = serde_json::from_reader(metadata_file)?;
            let modified = DateTime::<Utc>::from(modified);

            workflows.push(Workflow {
                id: workflow_id.to_string(),
                name: metadata.name.unwrap_or("<unnamed workflow>".to_string()),
                modified,
                dir: workflow_dir,
            });
        }

        workflows.sort_by(|x, y| y.modified.cmp(&x.modified));

        self.workflows = workflows;

        Ok(())
    }

    fn read_logs(&mut self) -> Result<()> {
        let workflow = &self.workflows[self.workflow_table_state.selected().unwrap() - 1];
        let logs_path = workflow.dir.path().join("logs");

        self.logs_buffer.clear();
        let mut log_file = File::open(logs_path)?;
        log_file.read_to_string(&mut self.logs_buffer)?;

        Ok(())
    }

    #[allow(unstable_name_collisions)]
    fn format_logs(&self) -> Vec<Line<'_>> {
        self.logs_buffer
            .lines()
            .map(|line| {
                let spans = line
                    .split_whitespace()
                    .map(|word| match word {
                        "START" => word.blue(),
                        "RUNNING" => word.yellow(),
                        "COMPLETE" => word.green(),
                        "ERROR" => word.red(),
                        _ => Span::raw(word),
                    })
                    .intersperse(Span::raw(" "));
                Line::default().spans(spans)
            })
            .collect()
    }

    fn read_errors(&mut self) -> Result<()> {
        let workflow = &self.workflows[self.workflow_table_state.selected().unwrap() - 1];

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

            let definition_file_path = error_file_path.parent().unwrap().join("definition");
            let definition_file = File::open(definition_file_path)?;
            let definition: Definition = serde_json::from_reader(definition_file)?;

            self.error_function = definition.function_name;
        }

        Ok(())
    }

    fn render(&mut self, frame: &mut Frame) {
        if !self.selected {
            self.render_menu(frame);
        } else {
            self.render_workflow(frame);
        }
    }

    fn render_menu(&mut self, frame: &mut Frame) {
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

        for workflow in &self.workflows {
            let cells = [
                Cell::new(workflow.id.clone()),
                Cell::new(workflow.name.clone()),
                Cell::new(format!("{:?}", workflow.modified)),
            ];
            rows.push(Row::new(cells));
        }
        let table = Table::new(
            rows,
            [
                Constraint::Length(36),
                Constraint::Min(32),
                Constraint::Min(32),
            ],
        )
        .row_highlight_style(Style::new().blue())
        .highlight_symbol(">>");

        frame.render_stateful_widget(table, frame.area(), &mut self.workflow_table_state);
    }

    fn render_workflow(&mut self, frame: &mut Frame) {
        let workflow = &self.workflows[self.workflow_table_state.selected().unwrap() - 1];
        let block = Block::new()
            .title(workflow.name.clone())
            .borders(Borders::all());

        self.logs_scroll_state = self
            .logs_scroll_state
            .content_length(self.logs_buffer.lines().count());
        let log_lines = self.format_logs();
        let logs = Paragraph::new(log_lines)
            .wrap(Wrap { trim: true })
            .scroll((self.logs_scroll as u16, 0))
            .block(block);

        let log_scroll = Scrollbar::new(ratatui::widgets::ScrollbarOrientation::VerticalRight)
            .begin_symbol(Some("↑"))
            .end_symbol(Some("↓"));

        if self.has_error {
            let layout =
                Layout::vertical([Constraint::Min(1), Constraint::Max(25)]).split(frame.area());

            frame.render_widget(logs, layout[0]);
            frame.render_stateful_widget(
                log_scroll,
                layout[0].inner(Margin {
                    // using an inner vertical margin of 1 unit makes the scrollbar inside the block
                    vertical: 1,
                    horizontal: 0,
                }),
                &mut self.logs_scroll_state,
            );

            let error_block = Block::new()
                .title(self.error_function.clone())
                .borders(Borders::all())
                .red();

            let error = Paragraph::new(self.error_buffer.clone())
                .wrap(Wrap { trim: false })
                .block(error_block);

            frame.render_widget(error, layout[1]);
        } else {
            let area = frame.area();
            frame.render_widget(logs, frame.area());
            frame.render_stateful_widget(
                log_scroll,
                area.inner(Margin {
                    // using an inner vertical margin of 1 unit makes the scrollbar inside the block
                    vertical: 1,
                    horizontal: 0,
                }),
                &mut self.logs_scroll_state,
            );
        }
    }
}
